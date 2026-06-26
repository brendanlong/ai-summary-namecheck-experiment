import sanitize, pathlib
raw = pathlib.Path("corpus/raw/gwern__nicotine.md").read_text()
print("raw occurrences:", raw.count("2004-hughes"))
body = sanitize.strip_front_matter(raw)
b = sanitize.scrub_identifiers(sanitize.markdown_to_prose(body), "gwern")
print("final-string occurrences:", b.count("2004-hughes"))
disk = pathlib.Path("corpus/clean-b/gwern__nicotine.txt").read_text()
print("disk occurrences:", disk.count("2004-hughes"))
