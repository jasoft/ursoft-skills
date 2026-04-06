---
name: remember
description: Remember and later find item content, features, dates, and locations using a remote NocoDB database. Use when the user asks "remember this" or wants to store or find item-related facts.
---

# Remember My Stuff

Use this skill when the user asks to **remember item-related facts** or **find stored facts**.
It uses a remote NocoDB database to store item names plus flexible content such as locations, dates, birthdays, features, events, reminders, or notes.

## Portability

This skill is installable on any machine.

- NocoDB connection details are read from environment variables or CLI flags.
- No local machine paths are required.
- The script defaults to the current working directory when it needs a scratch `tmp/` folder.

## Script Location

`skills/remember/scripts/manage_items.py`

## Configuration

Set these environment variables when running on a new machine:

- `REMEMBER_NOCODB_URL`
- `REMEMBER_NOCODB_API_TOKEN`
- `REMEMBER_NOCODB_TABLE_ID`
- `REMEMBER_WORKSPACE` optional, used only for image downloads

You can also pass the same values with command-line flags:

- `--url`
- `--token`
- `--table-id`

## Usage

### 1. Remember an Item

User: "Remember my watch is in the study, white cabinet, 3rd drawer." (or uploads an image and says "Remember this is my watch")

Action:
```bash
python3 skills/remember/scripts/manage_items.py add "watch" "study, white cabinet, 3rd drawer" --type "location" --image "/path/to/image.jpg"
python3 skills/remember/scripts/manage_items.py add "mom's birthday" "June 3" --type "date"
python3 skills/remember/scripts/manage_items.py add "charger" "black cable, USB-C, 2m" --type "feature"
python3 skills/remember/scripts/manage_items.py add "meeting" "tomorrow 10:00" --type "event"
```

After the add command succeeds, confirm that you used the `/remember` tool, then run `list` so the user can verify.

### 2. Find an Item

User: "Where is my watch?" / "When is mom's birthday?" / "What is the feature of my charger?" / "Remind me about tomorrow's meeting."

Action:
```bash
python3 skills/remember/scripts/manage_items.py find "watch"
python3 skills/remember/scripts/manage_items.py find "birthday"
python3 skills/remember/scripts/manage_items.py find "charger"
python3 skills/remember/scripts/manage_items.py find "meeting"
```

Output:
- The script prints the matched content and image path if it exists.
- If the record contains an image, the script downloads it to `tmp/` under the active workspace or current directory.

Reply after find:
- Tell the user the matched fact.
- If the fact is a location, say that clearly.
- If the fact is a birthday, date, feature, or event, say that clearly too.
- Provide the local image path if available.

### 3. Update an Item

User: "I moved my watch to the bedroom." / "My mom's birthday is June 4 now." / "The charger is now the black one."

Action:
1. Find the item to get its ID: `python3 ... find "watch"`
2. Update the content and optionally add/change image:
```bash
python3 skills/remember/scripts/manage_items.py update <ID> --content "bedroom" --type "location" --image "/path/to/new_image.jpg"
python3 skills/remember/scripts/manage_items.py update <ID> --content "June 4" --type "date"
python3 skills/remember/scripts/manage_items.py update <ID> --content "black one" --type "feature"
```

### 4. List All Items

User: "What items have you remembered?"

Action:
```bash
python3 skills/remember/scripts/manage_items.py list
```

### 5. Delete an Item

User: "Forget about the old watch."

Action:
1. Find the item first to get its ID: `python3 ... find "watch"`
2. Delete by ID:
```bash
python3 skills/remember/scripts/manage_items.py delete <ID>
```

## Tips

- When searching, the script uses fuzzy matching for item name, content, type, and note.
- If the user asks "Where is X?", try `find X`.
- If the user asks about birthdays, dates, features, or events, still use `find` with the key fact as the query.
- This database is shared with the user's NocoDB interface.
- 图片自动下载后会保存在 `tmp/` 目录。
- 找到多条记录时，先列候选项，再按需逐条处理。
- The script uses `REMEMBER_`-prefixed environment variables first, then CLI flags, and finally safe defaults where possible.

## Schema

The table structure is documented in `skills/remember/scripts/schema.sql`.
