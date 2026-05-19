# 🌈 417_Easing_Bridge

🌍 **Multilingual UI Supported (EN/JP/KR/CN)**

This is an easing add-on for Cascadeur.<br>
**SIMPLE, CONVENIENT, and AWESOME!**<br>

It will make your animations even MORE captivating 💫<br>

⚠️Currently in beta testing.

<br>

## 🎬 Reference Video

*Click to open **YouTube**.<br>
▶[417_Easing_Bridge Introduction Video<img width="960" height="540" alt="サムネ1" src="https://github.com/user-attachments/assets/dfe78911-b839-4670-b449-3e80d2b333f3" />
](https://youtu.be/ge5pJiImFQM)

<br>

## 🚀 Installation & Usage

This application is used by combining a **script for Cascadeur** and a **GUI application (.exe) for easing operations**.


## ■ Installation
1. Download the latest version from the [Releases page](../../releases).
2. Copy `easing_bridge.py` from the `to_Cascadeur` folder to Cascadeur's `commands` folder.<br>
　**Path example:** `C:\Program Files\Cascadeur\resources\scripts\python\commands`<br>

　Now you are ready to go.
 

## ■ Usage
1. Launch `417_Easing_Bridge.exe`.
2. Select an object and an interval of frames in Cascadeur.
3. Design the curve using the Easing Bridge GUI.
4. Press **Ctrl+B** / **Cmd+B** in Cascadeur to bake the curve.<br>
(Or go to Menu bar > `Commands` > `Easing Bridge_417` > `Bake`)
> 💡 How to register the shortcut: <br>
> Menu bar > `Settings` > `Hotkeys Window` > `Search: 417` > Register `[Ctrl+B]` to `[Easing Bridge_417.Bake]`

## ■ Shortcuts
[Cascadeur]<br>
- **Ctrl+B** / **Cmd+B** : Bake curve

[Graph App]<br>
- **Double-click** (Graph) : Add a control point
- **Alt+Click** (Anchor) : Reset tangent
- **Shift+Drag** (Tangent) : Symmetrical mirror
- **Alt+Drag** (Tangent) : X-axis mirror (V-shape)
- **Mouse Wheel** : Zoom in/out
- **Drag Background** : Pan view


## ■ Uninstallation
1. **Remove shortcut setting** <br>
　Delete the shortcut registered to `Easing Bridge_417.Bake` via Cascadeur's Menu bar > `Settings` > `Hotkeys Window` > `Search: 417`.
2. **Remove the script** <br>
　Delete `easing_bridge.py` from Cascadeur's `commands` folder.<br>
　Path example: `C:\Program Files\Cascadeur\resources\scripts\python\commands`
3. **Delete the application** <br>
　Move the extracted application folder (e.g., `417_easing_bridge_v0.9.0` folder) to the Recycle Bin.

<br>

## ⚠️ Precautions

- Always save (backup) your scene before applying easing.
- When applying, make sure to click the Cascadeur window to make it active.
- If you want to redo the easing, press `Ctrl+Z` to undo it first, then apply it again.
- The `Ctrl+B` shortcut will be automatically assigned upon the first launch.<br>(If it is already assigned to another function, the automatic registration will be skipped.)
- For curves that exceed the graph boundaries, rig parts may stretch or behave unusually due to the specifications of the rig structure.
- If it does not work properly, try restarting or reinstalling Cascadeur and this add-on.
- For other issues, please check the [issues](../../issues) page.
  If the problem persists, please contact the author via [issues](../../issues) / [X](https://x.com/417_Butter) / [YouTube](https://www.youtube.com/@417_Butter).

<br>

## 💻 SYSTEM REQUIREMENTS

- **OS**: Windows 11
- **Cascadeur**: ver. 2025.3 or later

<br>

## 📜 License

**All Rights Reserved.**<br>
The copyright of this software (including source code, executable files, UI design, and icon images) belongs to the author.<br>
Unauthorized redistribution, sale, or modification* is prohibited. (*Modification is allowed only for personal use within this add-on.)<br>
**Disclaimer**: Use this add-on at your own risk. The author is not responsible for any troubles or damages caused by its use.

<br>

## 🛠️ Dependencies & Credits

The GUI executable of this application is built using the following open-source projects:

- **[PySide6](https://doc.qt.io/qtforpython/)**: LGPL v3.0 License
- **[Python](https://www.python.org/)**: PSF License
- *(If there are any other libraries used, such as pynput, list them here)*

<br>

## 🎁 SPECIAL OFFER

🌐 **Get 15% OFF Cascadeur plans!**<br>
　 Promo Code: Butter<br>
　 ▶[Cascadeur Official Purchase Page Here!](https://cascadeur.com/plans?ref=Butter)

<br>

🎬 **I also make [Cascadeur tutorials](https://www.youtube.com/@417_Butter) on Youtube!**

- Creator(417_Butter)：[X](https://x.com/417_Butter) | [YouTube](https://www.youtube.com/@417_Butter) | [GitHub](https://github.com/417-Butter/417_easing_bridge#-417_easing_bridge)
