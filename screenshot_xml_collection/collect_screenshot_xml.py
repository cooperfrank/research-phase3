"""
Android UI Hierarchy XML and Screenshot Collector

Connects to an Android device via UIAutomator2 and captures the current UI hierarchy
as an XML dump and a screenshot. The XML file is saved to the xmls/ directory and the
screenshot is saved to the screenshots/ directory with a user-specified filename.

Usage:
    python collect_screenshot_xml.py <filename>
"""

import sys
import os
import uiautomator2 as u2

if len(sys.argv) != 2:
    print("Usage: python collect_screenshot_xml.py <filename>")
    sys.exit(1)

filename = sys.argv[1]

# Ensure xmls and screenshots directories exist
os.makedirs("xmls", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)

# Connect to device and capture both XML and screenshot
d = u2.connect()
xml = d.dump_hierarchy()

# Save XML to xmls/<filename>
xml_output_path = os.path.join("xmls", f"{filename}.xml")
with open(xml_output_path, "w", encoding="utf-8") as f:
    f.write(xml)

# Save screenshot to screenshots/<filename> (replace .xml with .png if needed)
screenshot_filename = filename.rsplit('.', 1)[0] + '.png' if '.' in filename else filename + '.png'
screenshot_output_path = os.path.join("screenshots", screenshot_filename)
d.screenshot(screenshot_output_path)

print(f"XML dump saved to {xml_output_path}")
print(f"Screenshot saved to {screenshot_output_path}")
print(d.info)