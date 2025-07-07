### Installation

Install [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)

Install `wialonblock` with `uv tool`

```shell
uv tool install wialonBlock@https://github.com/o-murphy/wialonBlock.git
```

### Run

Create `.env.toml` config, an
example [can be found on repo](https://github.com/o-murphy/wialonBlock/blob/master/.env.example.toml)

Run the app from dir where the `.env.toml` is placed

```shell
wialonblock
```

Or use path to config

```shell
wialonblock path/to/your/.env.toml
```

Redirect logging stdout

```shell
wialonblock > path/where/save/wialonblock.log
```

### Bot commands

```shell
/list - Display all units
/get_group_id - Get current chat/group ID
<string> - Search by pattern string
/i <string> - This message will be ignored by search handler
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

### Run in docker

```shell
docker build -t wialonblock .
mkdir -p log
touch .env.toml  # adjust content to your own
docker run -d \
  --name wialonblock \
  -e CONFIG_PATH=/app/.env.toml \
  -e LOG_PATH=/app/log/logfile \
  -v "$(pwd)/.env.toml:/app/.env.toml" \
  -v "$(pwd)/log:/app/log" \
  --restart unless-stopped \
  wialonblock
```

