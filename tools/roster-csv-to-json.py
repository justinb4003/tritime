import sys
import json
import pandas as pd


roster_df = None
if len(sys.argv) <= 1:
   print("No arguments were given")
   sys.exit(-1)
else:
    for arg in sys.argv[1:]:
        print(arg)
        df = pd.read_csv(arg)
        roster_df = df if roster_df is None else pd.concat([roster_df, df])

with open('../badges.json', 'r') as f:
    existing = json.load(f)

# iterate through the existing dict
for badge, data in existing.items():
    print(badge)
    print(data)
