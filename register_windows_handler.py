"""CRIS Windows Protocol Handler Registration Utility.

Registers/unregisters `cris_launcher.py` as a Windows HTTP and HTTPS protocol handler
under HKEY_CURRENT_USER so non-admin users can route desktop links to CRIS.
"""

import json
import os
import sys

CONFIG_FILE_NAME = "cris_config.json"
PROT_NAME_HTTP = "CRISLauncher.HTTP"
PROT_NAME_HTTPS = "CRISLauncher.HTTPS"
APP_REG_KEY = r"Software\CRISLauncher\Capabilities"


def get_paths():
    """Return python executable, script path, and config path."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, "cris_launcher.py")
    cfg_path = os.path.join(current_dir, CONFIG_FILE_NAME)

    # Use pythonw.exe if available to avoid flashing terminal window on link click
    py_dir = os.path.dirname(sys.executable)
    pyw_exe = os.path.join(py_dir, "pythonw.exe")
    python_exe = pyw_exe if os.path.isfile(pyw_exe) else sys.executable

    return python_exe, script_path, cfg_path


def detect_and_save_real_browser(cfg_path: str) -> str:
    """Find the real browser binary and record it in cris_config.json."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ]

    selected_browser = ""
    for exe in candidates:
        if exe and os.path.isfile(exe):
            selected_browser = exe
            break

    cfg_data = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
        except Exception:
            cfg_data = {}

    if selected_browser:
        cfg_data["real_browser_path"] = selected_browser
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=2)

    return selected_browser


def register_handler() -> bool:
    """Register CRIS Launcher in HKCU registry for HTTP and HTTPS protocols."""
    if sys.platform != "win32":
        print("[CRIS Register] Protocol registration is only supported on Windows.")
        return False

    import winreg

    python_exe, script_path, cfg_path = get_paths()
    real_browser = detect_and_save_real_browser(cfg_path)

    cmd_string = f'"{python_exe}" "{script_path}" "%1"'

    try:
        # 1. Register HTTP command
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTP}\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, cmd_string)

        # 2. Register HTTPS command
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTPS}\shell\open\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, cmd_string)

        # 3. Register Application Capabilities
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APP_REG_KEY) as key:
            winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, "CRIS Link Guard Launcher")
            winreg.SetValueEx(key, "ApplicationDescription", 0, winreg.REG_SZ, "CRIS Web3 Phishing Interceptor for Windows")

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{APP_REG_KEY}\UrlAssociations") as key:
            winreg.SetValueEx(key, "http", 0, winreg.REG_SZ, PROT_NAME_HTTP)
            winreg.SetValueEx(key, "https", 0, winreg.REG_SZ, PROT_NAME_HTTPS)

        # 4. Register in RegisteredApplications
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            winreg.SetValueEx(key, "CRISLauncher", 0, winreg.REG_SZ, APP_REG_KEY)

        print("[CRIS Register] Successfully registered CRIS Launcher in Windows Registry!")
        print(f"  Command: {cmd_string}")
        print(f"  Downstream browser saved: {real_browser or 'None (using standard fallback)'}")
        print("  Note: Set CRIS Launcher as your Default Web Browser in Windows Settings to complete activation.")
        return True

    except Exception as err:
        print(f"[CRIS Register] Failed to write registry entries: {err}", file=sys.stderr)
        return False


def unregister_handler() -> bool:
    """Remove CRIS Launcher keys from HKCU registry."""
    if sys.platform != "win32":
        print("[CRIS Register] Protocol unregistration is only supported on Windows.")
        return False

    import winreg

    def delete_key_tree(root, subkey):
        try:
            with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                        delete_key_tree(root, rf"{subkey}\{child}")
                    except OSError:
                        break
            winreg.DeleteKey(root, subkey)
        except OSError:
            pass

    try:
        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTP}")
        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTPS}")
        delete_key_tree(winreg.HKEY_CURRENT_USER, r"Software\CRISLauncher")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_ALL_ACCESS) as key:
                winreg.DeleteValue(key, "CRISLauncher")
        except OSError:
            pass

        print("[CRIS Register] Unregistered CRIS Launcher from Windows Registry.")
        return True
    except Exception as err:
        print(f"[CRIS Register] Failed to unregister: {err}", file=sys.stderr)
        return False


def check_registration_status() -> dict:
    """Check whether registry keys are configured."""
    status = {"registered": False, "http_cmd": None, "https_cmd": None, "platform": sys.platform}
    if sys.platform != "win32":
        return status

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTP}\shell\open\command") as key:
            val, _ = winreg.QueryValueEx(key, "")
            status["http_cmd"] = val
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROT_NAME_HTTPS}\shell\open\command") as key:
            val, _ = winreg.QueryValueEx(key, "")
            status["https_cmd"] = val

        if status["http_cmd"] and status["https_cmd"]:
            status["registered"] = True
    except OSError:
        status["registered"] = False

    return status


def main():
    if "--unregister" in sys.argv:
        unregister_handler()
    elif "--status" in sys.argv:
        st = check_registration_status()
        print(json.dumps(st, indent=2))
    else:
        register_handler()


if __name__ == "__main__":
    main()
