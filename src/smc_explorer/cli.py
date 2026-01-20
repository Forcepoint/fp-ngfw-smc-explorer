#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

# -*- coding: utf-8 -*-
"""
CLI functions
"""

import click
import json
import logging
import os
import random
import sys
import signal

from importlib import metadata


from jmespath import search as jp

from .dict_utils import cleanup_dict
from .exceptions import CommandError, ResolveError, SMCOperationFailure
from .hname import resolve_hname, split_hname
from .py2hcl import dict_to_hcl

# from .smc_session import SMCSession
from .smc_client import SMCClient
from .smc_session import SMCSession
from .str_utils import to_snake

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

TFSMC_LOG_FILE = "/tmp/smc-explorer.log"


ATTRIBUTES_TO_SKIP = {
    "link",
    "key",
    "read_only",
    "system",
    "system_key",
    "etag",
    "locked",
    "trashed",
    "admin_domain",
    # TODO discrepancies with swagger
    "enable_saml_for_ssl_vpn",
    "disabled",
    "nondecrypted_ca_certificate_ref",
    "opcua_client_x509_credentials",
    "opcua_decryption_mode",
    "opcua_server_x509_credentials",
    "allow_long_userid_lookup",  # error 400 when trying to create
}


def configure_logging():
    tfsmc_debug = os.environ.get("SMC_EXPLORER_DEBUG")
    tfsmc_log_file = TFSMC_LOG_FILE

    default_level = logging.DEBUG if tfsmc_debug == "all" else logging.INFO

    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
        filename=tfsmc_log_file,
        # filemode='w',
        level=default_level,
    )


def get_smc_client() -> tuple[SMCClient, SMCSession]:
    """Initialize and return SMC client with session.

    returns:
        tuple: SMCClient instance and SMCSession instance
    """
    url = os.environ.get("TF_VAR_smc_url") or os.environ.get(
        "TF_VAR_url", "http://localhost:8082"
    )
    ver = os.environ.get("TF_VAR_smc_ver") or os.environ.get("TF_VAR_api_version")
    apikey = os.environ.get("TF_VAR_smc_apikey") or os.environ.get("TF_VAR_api_key")

    cert = os.environ.get("TF_VAR_trusted_cert")
    verify_ssl = os.environ.get("TF_VAR_verify_ssl", "true").lower() == "true"
    domain = os.environ.get("TF_VAR_domain", "Shared Domain")

    if not apikey or not url or not ver:
        click.echo(
            "missing mandatory TF_VAR_smc_ver, TF_VAR_smc_url or TF_VAR_smc_apikey",
            err=True,
        )
        sys.exit(1)

    session = SMCSession(
        url, ver, apikey, cert=cert, verify_ssl=verify_ssl, domain=domain
    )
    return SMCClient(session), session


@click.group(
    context_settings={"help_option_names": ["-h", "--help"], "show_default": True}
)
@click.version_option(
    metadata.version("smc-explorer"), "-v", "--version", message="%(version)s"
)
def cli():
    """SMC Explorer CLI tool."""
    configure_logging()


@cli.command()
def doc():
    """Show package documentation."""
    description = metadata.metadata("smc-explorer")["Description"]
    click.echo(description)


@cli.command(name="completion")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def setup_completion_command(shell) -> None:
    """Setup shell completion for the CLI."""
    if shell == "bash":
        click.echo(
            """# Copy this line to your terminal to update ~/.bashrc file
echo 'eval "$(_SMC_EXPLORER_COMPLETE=bash_source smc-explorer)"' >> ~/.bashrc"""
        )
    elif shell == "zsh":
        click.echo(
            """# Copy this line to your terminal to update ~/.zshrc file
echo 'eval "$(_SMC_EXPLORER_COMPLETE=zsh_source smc-explorer)"' >> ~/.zshrc"""
        )
    elif shell == "fish":
        click.echo(
            """# Copy this line to your terminal:
echo '_SMC_EXPLORER_COMPLETE=fish_source smc-explorer | """
            "source' > ~/.config/fish/completions/smc-explorer.fish"
        )


def _complete_hname(ctx, param, incomplete):
    """Complete the hierarchical name (hname) argument for the CLI
    commands."""
    smc_client, session = get_smc_client()
    # print(f"{param=}, {incomplete=}", file=sys.stderr)
    try:
        session.login()
        # todo remove last part of incomplete
        incomplete_split = incomplete.rsplit("/", 1)
        if len(incomplete_split) == 2:
            incomplete_parent, incomplete_child = incomplete_split
        else:
            incomplete_parent, incomplete_child = "", incomplete_split[0]
        res = smc_client.list(incomplete_parent)
        if not res:
            return []
        if incomplete_parent == "":
            return [f"{name}/" for name in res if name.startswith(incomplete_child)]
        else:
            return [
                f"{incomplete_parent}/{name}/"
                for name in res
                if name.startswith(incomplete_child)
            ]

    except Exception:
        # ignore any error and return empty list to avoid breaking
        # completion
        return []


@cli.command()
@click.argument("hname", required=False, shell_complete=_complete_hname)
def list(hname):
    """List the sub-elements under given hierarchical name (hname)."""
    smc_client, session = get_smc_client()

    try:
        session.login()
        try:
            res = smc_client.list(hname)
        except ResolveError as err:
            raise CommandError(err)
        except SMCOperationFailure as err:
            raise CommandError(err)

        for name in sorted(res):
            click.echo(name)
    except (BrokenPipeError, IOError):
        pass
    except Exception as exc:
        click.echo(f"Error {exc}. Check log {TFSMC_LOG_FILE}", err=True)
        logger.error("got exc", exc_info=True)
    finally:
        session.logout()


@cli.command()
@click.argument("hname", shell_complete=_complete_hname)
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["json", "hcl"]),
    default="hcl",
    help="Output format",
)
@click.option("-r", "--raw", is_flag=True, help="Show raw output")
@click.option("--hcl2", is_flag=True, help="Use HCL2 syntax")
@click.option("-o", "--output", help="Output file path")
@click.option("-n", "--name", "new_name", help="Rename resource")
@click.option("-s", "--skip", "skip_attrs", help="Skip attributes (comma separated)")
@click.option("-k", "--keep", "keep_attrs", help="Keep attributes (comma separated)")
@click.option(
    "-x",
    "--extra-clean",
    "remove_falsy",
    is_flag=True,
    help="Hide attr with false, -1, empty array and empty strings (use with care !!!)",
)
def show(hname, fmt, raw, hcl2, output, new_name, skip_attrs, keep_attrs, remove_falsy):
    """Retrieve an SMC element with its hierarchical name (hname) and display it."""
    smc_client, session = get_smc_client()

    try:
        session.login()
        if output:
            dest = open(output, "w")
        else:
            dest = sys.stdout
        try:
            smc_element = smc_client.get(hname)
        except ResolveError as err:
            raise CommandError(err)
        except SMCOperationFailure as err:
            raise CommandError(err)

        elt = smc_element.data
        out = ""

        name_parts = split_hname(hname)
        is_odd = len(name_parts) % 2 == 1

        res_type = jp("link[?rel=='self'].type|[0]", elt)
        if not res_type:
            res_type = name_parts[-1 if is_odd else -2]

        elt_clean = None

        if new_name:
            res_name = new_name
            if "name" in elt:
                elt["name"] = new_name
        else:
            res_name = elt.get("name")
            if not res_name:
                if is_odd:
                    res_name = (
                        res_type + "_noname" + random.randint(1000, 9999).__str__()
                    )
                else:
                    res_name = name_parts[-1]
        if raw:
            elt_clean = elt
        else:
            skip_list = ATTRIBUTES_TO_SKIP
            keep_list = set()
            if skip_attrs:
                skip_list = skip_list.union(
                    set([x.strip() for x in skip_attrs.split(",")])
                )
            if keep_attrs:
                keep_list = set([x.strip() for x in keep_attrs.split(",")])
            elt_clean = cleanup_dict(elt, skip_list, keep_list, remove_falsy)

        if fmt == "json":
            out = json.dumps(elt_clean, indent=4)
            print(out, file=dest)
            suffix = ".json"
        elif fmt == "hcl":
            print(
                'resource "smc_'
                + res_type
                + '" "'
                + to_snake(res_name).lower()
                + '" {',
                file=dest,
            )
            use_blocks = not hcl2 if hcl2 is not None else False
            out = dict_to_hcl(elt_clean, indent=1, use_blocks=use_blocks)
            print(out, file=dest)
            print("}", file=dest)
            suffix = ".tf"
        else:
            raise CommandError(f"format {fmt} not supported")
        if output:
            dest.close()
            click.echo(f"Wrote resource to {output}")
    except (BrokenPipeError, IOError):
        pass
    except Exception as exc:
        click.echo(f"Error {exc}. Check log {TFSMC_LOG_FILE}", err=True)
        logger.error("got exc", exc_info=True)
    finally:
        session.logout()


@cli.command()
@click.argument("hname", shell_complete=_complete_hname)
def delete(hname):
    """Delete an element with its hierarchical name (hname)."""
    smc_client, session = get_smc_client()

    try:
        session.login()
        try:
            smc_elt = smc_client.get(hname)
            smc_client.delete(smc_elt)
        except ResolveError as err:
            raise CommandError(err)
        except SMCOperationFailure as err:
            raise CommandError(err)
    except (BrokenPipeError, IOError):
        pass
    except Exception as exc:
        click.echo(f"Error {exc}. Check log {TFSMC_LOG_FILE}", err=True)
        logger.error("got exc", exc_info=True)
    finally:
        session.logout()


@cli.command("get-url")
@click.argument("hname", shell_complete=_complete_hname)
def get_url(hname):
    """Convert a hierarchical name (hname) into the corresponding URL."""
    smc_client, session = get_smc_client()

    try:
        session.login()
        try:
            url = resolve_hname(session, hname)
        except ResolveError as err:
            raise CommandError(err)
        except SMCOperationFailure as err:
            raise CommandError(err)

        click.echo(url)
    except (BrokenPipeError, IOError):
        pass
    except Exception as exc:
        click.echo(f"Error {exc}. Check log {TFSMC_LOG_FILE}", err=True)
        logger.error("got exc", exc_info=True)
    finally:
        session.logout()


def main():
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    cli()


if __name__ == "__main__":
    main()
