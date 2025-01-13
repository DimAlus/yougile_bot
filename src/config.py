import toml

_cnf = None
with open("./config.toml", "r") as f:
  _cnf = toml.load(f)

config = {
  **_cnf,
  "users": { v: f"@{k}" for k, v in _cnf["users"].items() },
}
print(config)

