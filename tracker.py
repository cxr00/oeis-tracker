from datetime import datetime, timedelta
import json
import os
import praw
import requests


class OEISTracker:
    """
    Run once (manually for now) every Sunday

    Use OEISTracker().post_to_subreddit(debug, test, update)
    """
    def __init__(self):
        print("Initializing client...")
        self.reddit = praw.Reddit(
            user_agent=f"windows:{os.environ.get('REDDIT_OEIS_ID')}:1.0 (by u/OEIS-Tracker)",
            client_id=os.environ.get("REDDIT_OEIS_ID"),
            client_secret=os.environ.get("REDDIT_OEIS_SECRET"),
            username="OEIS-Tracker",
            password=os.environ.get("REDDIT_OEIS_PW")
        )
        self.search_string = "https://oeis.org/search?fmt=json&q=keyword:new&start={}"
        self.pull = []
        self.data = None
        self.post = None

        print("Loading previous new sequences...")
        with open("prev.txt", "a+") as f:  # Ensure file exists
            pass
        with open("prev.txt", "r") as f:
            self.prev = [int(k) for k in f.read().split("\n") if k]

    def get_recent_new_sequences(self):
        print("Retrieving recent new sequences...")
        oeis_sess = requests.Session()
        count = json.loads(
            oeis_sess.get(
                self.search_string.format(1)
            ).text
        )["count"]
        print(f"Count of {count} recent new sequences retrieved.")

        mod = count % 10

        print(f"Retrieving all pages...")
        for grab in range(0, count+1, 10):
            self.pull.extend(
                json.loads(
                    oeis_sess.get(
                        self.search_string.format(count - grab - mod)
                    ).text
                )["results"]
            )
            print(".", end="")
        oeis_sess.close()
        print()

        print(f"Retrieved {len(self.pull)} sequences.")
        return self.pull

    def organize_data(self):
        print("Organizing data pulled from oeis.org...", end="")
        self.data = {}
        new_prev = []
        brand_new = []
        for each in self.pull:
            if each["number"] not in self.prev:
                seq = each["data"].split(",")
                seq = ", ".join(seq[:5]) + ("..." if len(seq) >= 5 else "")
                self.data[f"A{each['number']}"] = {
                    "link": f"https://oeis.org/A{each['number']}",
                    "name": each["name"],
                    "seq": seq,
                }
                brand_new.append(each["number"])
            new_prev.append(each["number"])
        self.prev = list(set(new_prev).intersection(set(self.prev))) + brand_new
        print("Data organized.")

    def create_post(self):
        print(f"Creating post with {len(self.data.keys())} recent new sequences...", end="")
        self.post = []
        self.post.append("|OEIS number|Description|Sequence|")
        self.post.append("|-|-|-|")
        for key, value in sorted(self.data.items(), key=lambda x: x[0]):
            name = value["name"].replace("|", "\|")
            self.post.append(f"|[{key}]({value['link']})|{name}|{value['seq']}|")
        self.post = "\n".join(self.post)
        print("Post created.")

    def post_to_subreddit(self, debug=False, test=False, update=True):
        """
        Gather, organize, create and post to r/OEIS

        :param debug: When True, simply print results and refrain from posting
        :param test: When True, post to r/test instead of r/OEIS
        :param update: When True, update prev.txt
        """

        self.get_recent_new_sequences()
        self.organize_data()
        if not self.data:
            print("No new sequences to report. Refraining from posting.")
            return

        self.create_post()

        today = datetime.date(datetime.now())
        idx = (today.weekday() + 1) % 7
        sunday = today - timedelta(idx)
        if debug:
            print()
            print(f"New OEIS sequences - week of {sunday.strftime('%m/%d')}")
            print(self.post)
            print()
        else:
            print(f"Posting to r/{'test' if test else 'OEIS'}...", end="")
            self.reddit.subreddit("test" if test else "oeis").submit(
                title=f"New OEIS sequences - week of {sunday.strftime('%m/%d')}",
                selftext=self.post
            )
            print("Post complete.")

        if update:
            print("Recording recent newest sequences in prev.txt...", end="")
            with open("prev.txt", "w") as f:
                f.write("\n".join([str(k) for k in self.prev]))
            print("Saved.")


if __name__ == "__main__":
    # post_to_subreddit <- create_post <- organize_data <- get_recent_new_sequences
    OEISTracker().post_to_subreddit(debug=False, test=False, update=True)
