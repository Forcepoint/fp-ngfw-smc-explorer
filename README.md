
smc-explorer is a companion tool for the forcepoint terraform smc
provider. It allows to dump the elements already existing in the smc
in hcl format and obtain the names and types of resources to use as a
reference in your terraform config files (eg "tcp_service/SSH").

# pre-requisites

- python >=3.10

# quick start

(you can use pip instead of pipx)

```bash
# install
$ pipx install --force git+https://github.com/Forcepoint/fp-ngfw-smc-explorer.git

# configure credentials
$ export TF_VAR_smc_apikey="xxxxxx"
$ export TF_VAR_smc_url="http://localhost:8082"
$ export TF_VAR_smc_ver="7.3"

# explore resources using "list" and "show"
$ smc-explorer list
...
$ smc-explorer show tcp_service/SSH
...
$ smc-explorer show 'fw_policy/Lab FW1/fw_ipv4_access_rules/Rule @2097357.0' -f json
...
$ smc-explorer show single_fw/myfw -o /tmp/myfw.tf
```

# install

## installation from github repo with pipx

(you can use pip instead of pipx)

```bash
pipx install --force git+https://github.com/Forcepoint/fp-ngfw-smc-explorer.git
```

to uninstall:

```bash
pipx uninstall smc-explorer
```


## test without installing (needs uvx)

```sh
uvx --from git+https://github.com/Forcepoint/fp-ngfw-smc-explorer.git smc-explorer
```

## installation from github repo with uv

```sh
uv tool install git+https://github.com/Forcepoint/fp-ngfw-smc-explorer.git
```

to uninstall:

```bash
uv tool uninstall smc-explorer
```


## install from local clone (development version)

```sh
git clone https://github.com/Forcepoint/fp-ngfw-smc-explorer.git
make install
```



# configure

the variables names are the same as the smc terraform provider
attributes.

## http

```bash
export TF_VAR_url="http://localhost:8082"
export TF_VAR_api_key="xxxxxx"
export TF_VAR_api_version="7.4"
```

## https

note: you might encounter a problem with the smc CA certificate if
installing smc-explorer with python 3.13 (certificate verify failed:
Path length given without key usage keyCertSign). In this case:

- use python 3.12
- disable verify_ssl
- sign with your own CA

```bash
export TF_VAR_url="https://localhost:8082"
export TF_VAR_api_key="xxxxxx"
export TF_VAR_api_version="7.4"
export TF_VAR_trusted_cert="$(cat certificate1768396249572.crt)"
export TF_VAR_verify_ssl=true
```

## completion

### for bash

```sh
echo 'eval "$(_SMC_EXPLORER_COMPLETE=bash_source smc-explorer)"' >> ~/.bashrc
```

### for zsh

```sh
echo 'eval "$(_SMC_EXPLORER_COMPLETE=zsh_source smc-explorer)"' >> ~/.zshrc
```

### for fish

```sh
echo '_SMC_EXPLORER_COMPLETE=fish_source smc-explorer | source' > ~/.config/fish/completions/smc-explorer.fish
```

# usage

## run script

if you have installed the script in ~/.local/bin

```bash
~/.local/bin/smc-explorer
```

## list all resource types

```bash
$ smc-explorer list
```

## list all instances of a given resource type

```bash
$ smc-explorer list 'fw_policy'
```
## list all sub-resources of a given resource

```bash
$ smc-explorer list 'fw_policy/Lab FW1'
```

## list sub-resource

```bash
$ smc-explorer list 'fw_policy/Lab FW1/fw_ipv4_access_rules/Rule @2097357.0'
```

## show resource or sub-resource in terraform format

```bash
$ smc-explorer show 'fw_policy/Lab FW1/fw_ipv4_access_rules/Rule @2097357.0'
```

This sub-command has several options:

  -h, --help            show this help message and exit
  -f, --format {json,hcl,yaml,toml}
  -r, --raw
  -o, --output OUTPUT
  -n, --name NAME       rename resource
  -s, --skip SKIP       skip attributes (comma separated)
  -k, --keep KEEP       keep attributes (comma separated)
  -x, --extra-clean     hide attr with false, -1, empty array and empty strings (use with care !!!)

## show resource skipping some attributes

it is possible to use wildcards to specify the attributes to skip.
the command below removes the alias_value and antivirus attributes.

```bash
smc-explorer show single_fw/myfw  -x -s alias_value,antivirus
```


## show resource keeping only some attributes

it is possible to use wildcards to specify the attributes to keep.
the command below gives a summary of the firewall

```bash
smc-explorer show single_fw/myfw  -k '*interface*,name,address'
```

## show resource discarding only some attributes

```bash
smc-explorer show single_fw/myfw  -x -s alias_value,antivirus -k '*interface*,name,address'
```


## follow links from any attribute

in the example below, we follow the "default_alias_value" attribute.
the path part expression must be in jmespath syntax


```bash
$ smc-explorer show 'alias/$ Allowed SSH Local Sources'
resource "alias" "$ Allowed SSH Local Sources" {
  admin_domain = "http://localhost:8082/7.4/elements/admin_domain/1"
  default_alias_value = ["http://localhost:8082/7.4/elements/address_range/1"]
  locked = false
  name = "$ Allowed SSH Local Sources"
  trashed = false
}
$ smc-explorer show 'alias/$ Allowed SSH Local Sources/default_alias_value[0]'
resource "address_range" "NONE" {
  admin_domain = "http://localhost:8082/7.4/elements/admin_domain/1"
  ip_range = "0.0.0.0"
  locked = false
  name = "NONE"
  trashed = false
}

```

## show resource in json format

```bash
$ smc-explorer show single_fw/Plano -f json
```

## show resource with url

```bash
$ smc-explorer show 'http://localhost:8082/7.3/elements/user_id_service/4309'
```

## delete a resource

```bash
$ smc-explorer delete host/AExampleHost
```

## get the url by name

```bash
$ smc-explorer get-url host/AExampleHost
```






# troubleshooting

- log is in /tmp/smc-explorer.log
- export SMC_EXPLORER_DEBUG=all

# dev
## pre-requisites for dev

you need
- python >=3.10
- make
- uv (can be installed via pip)

```bash
pip install uv
```

## clone repo

```
git clone https://github.com/Forcepoint/fp-ngfw-smc-explorer.git
```

## install from clone

this installs smc-explorer in ~/.local/bin

```bash
make install
```

## run from the cloned repo

```bash
uv run smc-explorer
```
