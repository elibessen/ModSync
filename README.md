# ModSync

> A lightweight desktop tool that scans, detects, and updates Minecraft Fabric Mods automatically.

This project was created to simplify the process of keeping Fabric mods up to date.

I was getting frustrated with having to manually update mods every time a new Minecraft version dropped. Checking compatibility, downloading files, and replacing jars became repetitive and error-prone, especially when managing multiple mods at once.

This tool automates that process by:

- Detecting installed Fabric mods
Checking for compatible updates on Modrinth
Downloading and replacing outdated versions safely

- The goal is to reduce manual maintenance and make mod management more consistent across Minecraft updates.

## Requirements
- Windows
- Python 3.10+
- Internet Connection (for remote mod sources)
- Minecraft installed in standard `.minecraft` directory
- Minecraft must have Fabric installed using the official Fabric Installer:
https://fabricmc.net/use/installer/

## Privacy

- This application runs locally and does not collect or transmit personal data.
- It accesses the local `.minecraft` folder to read installed mods and Minecraft versions, and to update mod files. This information is not transmitted anywhere.
- Internet usage is limited to the Modrinth API for searching and downloading mod updates. No telemetry, analytics, or tracking is included.

## Project Structure
├── app.py → UI layer (CustomTkinter) \
├── updater.py → Core mod detection + update logic\
├── config.json → Minecraft version config

## Supported Mod Format
- Fabric mods only
- `.jar` files with `fabric.mod.json` (Forge / NeoForge mods are ignored)

## Safety Notes
- Old mod files are removed only after successful download
- Temporary `.tmp` files are used during download
- No cloud or external data storage, all kept on device.
- Only Modrinth API is used

## Limitations
- Requires mods to exist on Modrinth
- Cannot update mods not published on Modrinth
- Fabric only (no Forge Support)
- Version detection depends on `.minecraft/versions`

## Known Issues
- Some launchers (Prism, CurseForge) may use different `.minecraft` paths
- Custom mod folders are not detected
- Some mod IDs may not match Modrinth project slugs perfectly

## Future Improvments
- CurseForge/Prism launcher Support
- Parallel downloads
- Mod version rollback
- GUI progress bars per mod

## License
Licensed under MIT

## Attribution

This project uses the Fabric logo for UI purposes.
All trademarks and assets belong to their respective owners.

This project is not affiliated with FabricMC or Mojang.