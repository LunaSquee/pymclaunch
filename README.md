# pymclaunch
A [Minecraft](https://minecraft.net/en-us/) launcher library written in Python. Only third-party dependency is [requests](http://docs.python-requests.org/en/master/)!

### Common constructor

* **`clientRoot`** (string) - A path to the root directory of the Minecraft files (`~/.minecraft` is not recommended as the folder structure is different)
* **`mcVersion`** (string) - Minecraft version
* **`forgeVersion`** (string) - Forge Version (only on `MinecraftClientForge` class)
* **`gameName`** (string) - Name of the game directory
* **`authentication`**` = None ` (MojangAuthentication) - The `MojangAuthentication` instance to use. Contains the necessary arguments to launch a game with proper session information.
* **`jvm`**` = None ` (string) - A string of JVM Arguments

## MinecraftClient
Module `client` provides a `MinecraftClient` which can be used to install and launch vanilla Minecraft.

## MinecraftClientForge
Module `clientforge` provides a `MinecraftClientForge` which can be used to install and launch Minecraft, plus install Minecraft Forge and it's required libraries.

## MojangAuthentication
Module `authmojang` provides necessary functions to authenticate yourself against Mojang servers.

**WARNING!** Never store passwords in files! Only store the `accessToken` and then use the `refresh` method!

## Disclaimer
Minecraft is &copy; [Mojang AB](https://mojang.com/) - This repository does not infringe on the [Minecraft EULA](https://account.mojang.com/documents/minecraft_eula) and does not illegally distribute the game - all of the Minecraft files are downloaded from the official sources. You can purchase Minecraft from [their official store](https://minecraft.net/en-us/store/minecraft/).

## License
The MIT License

See [LICENSE](LICENSE)
