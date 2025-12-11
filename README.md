# Phase 3: Android UI Difference Detection via XML Hierarchy Analysis

*Conducted under Dingbang Wang and Prof. Tingting Yu*

## Overview
This is Phase 3 of our research project investigating methods to detect differences between Android screen elements. In the previous two phases, we utilized AI models like CLIP for visual comparison and semantic understanding of UI changes. In this phase, we are taking a different approach: instead of relying on image-based AI models, we directly read and compare the Android UI's XML hierarchy. This approach provides precise, structural analysis of UI changes by examining the actual element tree, attributes, and properties that define the interface.

## Methodology
Unlike image-based AI approaches (Phase 1 & 2), this XML-based method:

1. **Captures Ground Truth**: Accesses the actual UI element definitions rather than pixel representations
2. **Eliminates Visual Ambiguity**: Directly reads properties like enabled state, content descriptions, and resource IDs
3. **Structural Precision**: Knows exact element hierarchy, not just visual appearance
4. **Efficient Comparison**: Compares structured data rather than high-dimensional embeddings
5. **Interpretable Results**: Provides exact change types and locations

## UIAutomator2
This project leverages [UIAutomator2](https://github.com/openatx/uiautomator2), a Python wrapper for Android's UIAutomator framework that provides programmatic access to Android devices for testing and automation.

**Key Capabilities Used:**
- **`d.dump_hierarchy()`**: Extracts the complete UI element tree as XML, including all properties, attributes, and spatial information
- **`d.screenshot()`**: Captures device screen as PNG image
- **Device Connection**: Automatically connects to Android devices/emulators via ADB

**Why UIAutomator2?**
- Direct access to Android's accessibility hierarchy
- No need for rooting or special permissions
- Works with both physical devices and emulators
- Provides complete structural information about every UI element
- Captures the actual properties Android uses internally

## Project Components
### `screenshot_xml_collection/collect_screenshot_xml.py`

A data collection tool that captures synchronized pairs of screenshots and UI hierarchy dumps from Android devices/emulators.

**Features:**
- Connects to Android devices via UIAutomator2
- Captures current UI hierarchy as XML dump
- Takes synchronized screenshots of the device screen
- Saves XML files to `xmls/` directory
- Saves screenshots to `screenshots/` directory
- Command-line interface for easy batch collection

**Usage:**
```bash
python screenshot_xml_collection/collect_screenshot_xml.py <output_filename>
```

### `xmldiff.py`

A specialized comparison tool that analyzes two Android UI XML dumps and reports meaningful structural differences while filtering out cosmetic changes.

**Features:**
- **Intelligent Node Matching**: Matches UI elements between two XML trees using resource IDs, class names, content descriptions, and spatial positioning
- **Weighted Difference Scoring**: Calculates a normalized difference score (0-1) where:
  - 0.0 = Files are identical
  - 1.0 = Completely different
- **Change Classification**: Categorizes differences into:
  - Added/Removed elements (weight: 1.0)
  - Text changes (weight: 0.7)
  - Attribute changes (weight: 0.5)
  - Bounds/positioning changes (weight: 0.3)
- **Cosmetic Filtering**: Ignores visual styling attributes (textSize, textColor, background, etc.) to focus on functional changes
- **Detailed Output**: Provides JSON output with exact paths and change details

**Usage:**
```bash
python xmldiff.py base.xml input.xml
```

**Example:**
```bash
python xmldiff.py screenshot_xml_collection/xmls/home.xml screenshot_xml_collection/xmls/settings.xml
```

**Output:**
```
Difference Score: 0.2345 (0=identical, 1=completely different)
Total Differences: 15

[
  {
    "type": "text_change",
    "path": "/hierarchy[0]/android.widget.TextView[2]",
    "class": "android.widget.TextView",
    "from": "Welcome",
    "to": "Hello"
  },
  ...
]
```