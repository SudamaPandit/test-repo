"""Export job candidates; no application submission."""
import argparse, json
from pathlib import Path
from jobfinder import search_jobs

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--query",default="senior data engineer")
    parser.add_argument("--include-unverified",action="store_true")
    parser.add_argument("--out",default="jobs.json")
    args=parser.parse_args()
    data=search_jobs(args.query,include_unverified=args.include_unverified)
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Found {len(data['jobs'])} candidates; {len(data['source_errors'])} source failures")
    for source,error in data["source_errors"].items():
        print(f"{source}: {error}")

if __name__=="__main__":
    main()
