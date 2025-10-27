# Dyskownik - Multi-Drive Google Drive Organizer

**Dyskownik** is a command-line tool designed to organize and aggregate data from multiple Google Drives with similar folder structures.  
It scrapes file and folder metadata, categorizes them automatically, and rebuilds an organized folder system with shortcuts and collections on Google Drive.

---

## Project Overview

Imagine having several Google Drives that share a similar folder layout (for example, *Semesters*, *Lecturers*, *Courses*).  
Dyskownik lets you connect to all of them, scan their contents, and merge matching folders or files into unified categories.

For example, if three drives have folders 'Sem1', 'Sem 1', and 'S1', Dyskownik can recognize them as aliases of the same category ('Semester 1') and combine their contents into one structured view.

---

## Workflow

1. **Scraping Drives** – The system connects to multiple Google Drives and retrieves information about files and folders in a multi-threaded manner.  
2. **Database Storage** – Retrieved data is stored in a database along with pre-defined categories for automatic categorization.  
3. **Categorization** – Files and folders are automatically assigned to categories based on defined rules and aliases.  
4. **Folder Structure Generation** – The system creates a new organized hierarchy on Google Drive, using real folders and shortcuts to represent categories.  
5. **CLI Commands** – All operations are controlled from the command line (e.g. adding aliases from JSON, updating database, or automated periodic synchronization).

---

## Main Functionalities

- Fetch Drive data and save as JSON  
- Initialize and update the database  
- Import scanned data  
- Set or create root folders  
- Generate aliases from folder names or category types  
- Load and update category definitions from JSON  
- Delete or recreate category types dynamically  
- Update Drive structure based on database  
- Start a background server for periodic scans and synchronization

---

## Category Types

Each **category type** defines how categories and their aliases map to actual files and folders.  
Supported aggregation types are:

### **1. Shortcut**
Each category creates a **shortcut** to a folder whose name matches one of its aliases.  
- Structure: 'CategoryType → Category as shortcut to matching folder'  
- Example:  
  - Category type: 'Drives'  
  - Categories: 'Drive1', 'Drive2', 'Drive3'  
  - Alias for 'Drive1': 'Drive 1' 
  - Alias for 'Drive2': 'Drive Second'  
  → The *Drive2* shortcut will be created pointing to the drive folder named *"Drive Second"*.


### **2. Collection**
The category folder collects **all files** from multiple folders that match any of its aliases.  
- Structure: 'CategoryType → Category → aggregated files/shortcuts from all matching folders'  
- Example:  
  - Category type: 'Semesters'  
  - Categories: 'Sem1', 'Sem2', 'Sem3'  
  - Aliases for 'Sem1': 'Sem1', 'Sem 1', 'S1'  
  → The folder *Sem1* will aggregate files from all folders named "Sem1", "Sem 1", or "S1".

### **3. Pattern**
Each category defines one or more **Regex patterns** to match files and folders by name.  
All matches are collected into the category folder.  
- Structure: 'CategoryType → Category → matched files/folders'  
- Example:  
  - Category type: 'Lecturers'  
  - Category: 'Jan Kowalski'  
  - Aliases (patterns): '/^.*Kowalski.*$/gmi'  
  → All files or folders matching this Regex across all drives are grouped in this category.

## 🧾 Example JSON Definition

Below is an example of a JSON configuration file defining a category type called `"Courses"` that groups folders and files from multiple drives using the collection aggregation type.

```json
{
  "category_type_name": "Courses",
  "aggregation_type": "collection",
  "categories": [
    {
      "canonical_name": "Computer Architecture",
      "aliases": [
        "CompArch",
        "Computer Architecture",
        "Architecture of Computers"
      ]
    },
    {
      "canonical_name": "Operating Systems",
      "aliases": [
        "OS",
        "Operating Systems",
        "System Programming"
      ]
    },
    {
      "canonical_name": "Data Structures and Algorithms",
      "aliases": [
        "DSA",
        "Data Structures",
        "Algorithms"
      ]
    },
    {
      "canonical_name": "Database Systems",
      "aliases": [
        "DB",
        "Databases",
        "Database Systems"
      ]
    },
    {
      "canonical_name": "Computer Networks",
      "aliases": [
        "Networks",
        "Computer Networks",
        "Networking"
      ]
    },
    {
      "canonical_name": "Software Engineering",
      "aliases": [
        "SWE",
        "Software Eng",
        "Software Engineering"
      ]
    }
  ],
  "unassigned_folders": []
}
```
