from datetime import datetime, timedelta
import json
import os
import praw
import requests


class OEISTracker:
    """
    Run once (manually for now) every Sunday
    """
    def __init__(self, first=False):
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
        self.post = None
        self.grab = 50
        self.first = first
        self.intro = "Hello! This bot, u/OEIS-Tracker, will make a post every Sunday and present newly-added sequences for your viewing pleasure. These posts will not be pinned. Enjoy!"

        print("Loading previous new sequences...")
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

        mod = count % 10

        for grab in range(0, count+1, 10):
            self.pull.extend(
                json.loads(
                    oeis_sess.get(
                        self.search_string.format(count - grab - mod)
                    ).text
                )["results"]
            )
        oeis_sess.close()

        print(f"Retrieved {len(self.pull)} recent new sequences.")
        return self.pull

    def create_post_and_update_prev(self):
        print("Creating post...")
        self.post = []
        count = 0
        for each in self.pull:
            if each['number'] not in self.prev:
                count += 1
                start = each["data"].split(",")
                start = ", ".join(start) if len(start) < 10 else ", ".join(start[:10]) + "..."
                self.post.append(f"**[A{each['number']}](https://oeis.org/A{each['number']})**: {each['name']} {start}")
                self.prev.append(each["number"])
        self.post = "\n\n".join(self.post)
        if self.first:
            self.post = "\n\n".join([self.intro, self.post])
        print(f"Post created with {count} recent new sequences.")

        print("Recording newest sequences in prev.txt...", end="")
        with open("prev.txt", "w") as f:
            f.write("\n".join([str(k) for k in self.prev]))
        print("Saved.")

    def post_to_subreddit(self, debug=False, test=False):
        self.get_recent_new_sequences()
        self.create_post_and_update_prev()
        if not self.post:
            print("No new sequences to report. Refraining from posting.")
            return
        today = datetime.date(datetime.now())
        idx = (today.weekday() + 1) % 7
        sunday = today - timedelta(idx)
        if debug:
            print(f"New OEIS sequences - week of {sunday.strftime('%m/%d')}")
            print(self.post)
            exit()
        print("Posting to r/OEIS...")
        self.reddit.subreddit("test" if test else "oeis").submit(
            title=f"New OEIS sequences - week of {sunday.strftime('%m/%d')}",
            selftext=self.post
        )


if __name__ == "__main__":
    OEISTracker(first=True).post_to_subreddit()
