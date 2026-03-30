import os

files_to_patch = [
    "supabase/migrations/20260313120000_critical_data_stores.sql",
    "supabase/aisha_full_migration.sql"
]

search_text = """CREATE UNIQUE INDEX IF NOT EXISTS idx_content_performance_content_id
  ON content_performance(content_id)
  WHERE content_id IS NOT NULL;"""

replace_text = """ALTER TABLE content_performance
  ADD CONSTRAINT content_performance_content_id_key UNIQUE (content_id);"""

for file_path in files_to_patch:
    with open(file_path, "r") as f:
        content = f.read()

    if search_text in content:
        content = content.replace(search_text, replace_text)
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Patched {file_path}")
    else:
        print(f"Could not find search text in {file_path}")
