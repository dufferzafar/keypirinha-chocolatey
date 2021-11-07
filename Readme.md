# Keypiriniha Chocolatey

This is a package for the fast keystroke launcher keypirinha (http://keypirinha.com/)

It allows you to search & install packages via Chocolatey.

![Search for a particular package](https://i.imgur.com/QwRKPOJ.png)

![Install or open page of a package](https://i.imgur.com/PCLkhcm.png)

![Opens an administrative powershell to install the package](https://i.imgur.com/QcmwtOv.png)

## Installation

1. If you have Package Control plugin installed, then you can just search for "Chocolatey" there and install this plugin.

2. Alternatively, download the latest package from the [releases page](https://github.com/dufferzafar/keypirinha-chocolatey/releases).
    * Move the downloaded package to your `InstalledPackages` folder located at:

    * `Keypirinha\portable\Profile\InstalledPackages` in Portable mode

    * Or `%APPDATA%\Keypirinha\InstalledPackages` in Installed mode (the final path would look like `C:\Users\%USERNAME%\AppData\Roaming\Keypirinha\InstalledPackages`)

## Todo

* List outdated packages
* Upgrade packages
* Uninstall packages
