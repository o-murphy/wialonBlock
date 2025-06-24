### Installation

Install [uv package manager](https://docs.astral.sh/uv/getting-started/installation/) 

Install `wialonblock` with `uv tool`
```shell
uv tool install wialonBlock@https://github.com/o-murphy/wialonBlock.git
```

### Run

Create `.env.toml` config, an example [can be found on repo](https://github.com/o-murphy/wialonBlock/blob/master/.env.example.toml)

Run the app from dir where the `.env.toml` is placed
```shell
wialonblock
```

Or use path to config
```shell
wialonblock path/to/your/.env.toml
```

### Update

Update the app using `uv tool upgrade`

```shell
uv tool upgrade wialonBlock
# or with url path
uv tool upgrade wialonBlock@https://github.com/o-murphy/wialonBlock.git
```

### Remove
Remove or backup your `.env.toml` config

Uninstall the package with `uv tool uninstall`
```shell
uv tool uninstall wialonBlock
```