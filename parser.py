
from __future__ import annotations

import re
import math
import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol, Tuple


import pandas as pd
from datetime import datetime, timezone
import json
import yt_dlp
import pickle
from pathlib import Path


def download_videos():

    ydl_opts = {
        "extract_flat": False,
        "skip_download": True,
        "ignoreerrors": True,
        # "playlistend": 20,
    }

    channel_url = "https://www.youtube.com/@stanfordonline/videos"


    def format_duration(seconds):
      if not seconds:
        return "N/A"
      seconds = int(seconds)
      m, s = divmod(seconds, 60)
      h, m = divmod(m, 60)
      return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def calculate_days_on_youtube(entry):
      upload_date_str = entry.get("upload_date")
      if upload_date_str:
        try:
          pub_date = datetime.strptime(upload_date_str, "%Y%m%d")
          return (datetime.now() - pub_date).days
        except ValueError:
          pass

      timestamp = entry.get("timestamp")
      if timestamp:
        pub_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return (datetime.now(timezone.utc) - pub_date).days

      return None


    output_file = "video_data.json"

    f = open(output_file, "w", encoding="utf-8")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Fetching channel info...")
        info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries", [])

        f.write("[\n")  # Start JSON array

        first_item = True
        for entry in entries:
          if not entry:
            continue

          video_id = entry.get("id") or entry.get("url")
          video_url = (
              f"https://www.youtube.com/watch?v={video_id}"
              if video_id and not video_id.startswith("http")
              else video_id
          )

          item = {
              "title": entry.get("title", "N/A"),
              "duration": entry.get("duration_string")
              or format_duration(entry.get("duration")),
              "views": entry.get("view_count", "N/A"),
              "days_on_youtube": calculate_days_on_youtube(entry),
              "publish_date": entry.get("upload_date")
              or entry.get("timestamp", "N/A"),
              "url": video_url,
          }

          # Add comma separator between items
          if not first_item:
            f.write(",\n")
          else:
            first_item = False

          # Save item directly to file
          json.dump(item, f, indent=4, ensure_ascii=False)

        f.write("\n]")  # End JSON array

    print(f"\nSaved items directly to '{output_file}'.")
# download_videos()


def parse_raw_video_data(raw_data):
    df = pd.DataFrame(raw_data)

    # Split into multiple columns automatically
    split_titles = df['title'].str.split(r'\s*\|\s*', expand=True)

    # (Optional) Rename columns to something descriptive
    if split_titles.shape[1] == 3:
        split_titles.columns = ['course','semester','lesson']
    else:
        split_titles.columns = [f'title_part_{i+1}' for i in range(split_titles.shape[1])]
        if 'course' not in split_titles.columns:
            split_titles['course'] = df['title']
        if 'lesson' not in split_titles.columns:
            split_titles['lesson'] = df['title']

    # Merge back with the original DataFrame
    df = pd.concat([df, split_titles], axis=1)

    df_courses = df.dropna().copy()

    def minutes(time):
        hms = time.split(':')
        h = m = s = 0
        if len(hms)>2:
            h, m, s = hms
        elif len(hms)>1:
            m, s = hms
        else:
            s = hms
        return int(h) * 60 + int(m)
    df_courses['duration_minutes'] = df_courses['duration'].apply(minutes)
    # Pattern matches department letters (including '&'), course digits, and optional letter suffix
    pattern = r'([A-Z]+(?:&[A-Z]+)?\s*\d+[A-Z]?)'

    # Extract course code into a new column
    df_courses['course_code'] = df_courses['course'].str.extract(pattern)
    df_courses['dept'] = df_courses['course_code'].str.replace(r'\d+[A-Za-z]*', '', regex=True).str.strip()

    df_courses = df_courses[~df_courses['course'].str.contains('Seminar|Webinar', na=False)]

    df_courses['average_views'] = df_courses[['views','days_on_youtube']].apply(lambda t: int(t.iloc[0])//int(t.iloc[1]), axis=1)
    return df_courses['course'].unique()
    # df_courses_grouped = df_courses.groupby(['dept','course','course_code'])[['days_on_youtube','average_views']].mean()
    # # print(df_courses_grouped.shape)
    # # df_courses_grouped.sort_values(by=['average_views'], ascending=False).head()

    # df_lessons_grouped = df_courses.groupby(['dept','course','course_code','lesson'])[['days_on_youtube','average_views']].mean()
    # # print(df_lessons_grouped.shape)
    # # df_lessons_grouped.sort_values(by=['average_views'], ascending=False).head()

    # df_courses_grouped.shape, df_lessons_grouped.shape

    # import matplotlib.pyplot as plt
    # from sklearn.cluster import DBSCAN
    # from sklearn.preprocessing import StandardScaler

    # # 1. Scale the features (essential for distance-based clustering)
    # scaler = StandardScaler()
    # X_scaled = scaler.fit_transform(
    #     df_lessons_grouped[['days_on_youtube', 'average_views']]
    # )

    # # 2. Initialize and fit DBSCAN
    # # eps: max distance between two samples for one to be considered in the neighborhood of the other
    # # min_samples: minimum samples in a neighborhood to form a core point
    # dbscan = DBSCAN(eps=0.5, min_samples=5)
    # df_lessons_grouped['cluster'] = dbscan.fit_predict(X_scaled)

    # # 3. View cluster counts (-1 represents noise/outliers)
    # print(df_lessons_grouped['cluster'].value_counts())
    # df_lessons_grouped.head()

    # df_cluster_grouped = df_lessons_grouped.groupby(['cluster'])[['average_views']].mean()
    # df_cluster_grouped

    # df_lessons_selected = df_lessons_grouped[df_lessons_grouped['cluster']==1].reset_index().copy()
    # # for s in df_lessons_selected['dept']:
    # #     print(s, df_lessons_selected[df_lessons_selected['dept']==s]['lesson'])

    # df_lessons_selected.to_csv('lessons_frequently_viewd.csv', index=False)

    # df_lessons_grouped[df_lessons_grouped['cluster']==1].reset_index().to_csv('lessons_frequently_viewd.csv', index=False)
    # df_lessons_grouped[df_lessons_grouped['cluster']==-1].reset_index().to_csv('lessons_outlier_viewd.csv', index=False)
    # df_lessons_grouped[df_lessons_grouped['cluster']==0].reset_index().to_csv('lessons_intent_viewd.csv', index=False)

    # df_lessons_grouped[df_lessons_grouped['cluster']==-1]



def categorize_course_name(name):
    cat1_pattern = re.compile(
        r"(Transformers|LLMs|Diffusion|Language Modeling|Supercycle|Economics)",
        re.IGNORECASE,
    )
    if cat1_pattern.search(name):
        return "Category 1: Generative AI, Frontier Models & Strategy"
    return "Category 2: Core AI, Domain Deep Learning & Software"


# --------------------------------------------------------------------------- #
# 1. Reward model: syntactic validity
# --------------------------------------------------------------------------- #
class ACTIONS:
    CLASSES = {
            "Category 1: Generative AI, Frontier Models & Strategy": 0, 
            "Category 2: Core AI, Domain Deep Learning & Software": 1
        }

class ReasoningRewardModel:
    """Scores a completion for presence/validity/detail of a thinking block."""


    """
    Deterministic rule-based *teacher* for gift-card title classification.

    Given a product title, `get_ground_truth_action` returns the correct
    one of 2 classes (
            "Category 1: Generative AI, Frontier Models & Strategy", 
            "Category 2: Core AI, Domain Deep Learning & Software"
            )
    via simple keyword rules. `get_policy_distribution` exposes that as a
    one-hot categorical distribution, matching the "teacher policy" shape
    used elsewhere in this codebase.
    """

    def __init__(self):
        self.action_map = {
            "Category 1: Generative AI, Frontier Models & Strategy": 0, 
            "Category 2: Core AI, Domain Deep Learning & Software": 1
        }
        self.actions = [
            "Category 1: Generative AI, Frontier Models & Strategy", 
            "Category 2: Core AI, Domain Deep Learning & Software"]
        self.num_actions = len(self.action_map)

    def get_ground_truth_action(self, title: str) -> int:
        """
        Deterministic Teacher Policy based on provided conditions.
        """
        t = title.lower()
        label = categorize_course_name(t)

        return self.action_map[label]

    def get_policy_distribution(self, title: str) -> List[float]:
        """One-hot distribution over the 7 action classes for `title`."""
        action_idx = self.get_ground_truth_action(title)
        probs = [0.0] * self.num_actions
        probs[action_idx] = 1.0
        return probs

    def compute_reward(self, prompt: str, completion: Optional[str] = None) -> float:
        """+1 if the predicted class matches the teacher's ground truth, else -1."""
        if completion is None:
            reward = max(self.get_policy_distribution(prompt))
            return 1.0 if reward > 0 else -1.0

        true_idx = self.get_ground_truth_action(prompt)
        true_label = self.actions[true_idx]
        return 1.0 if completion == true_label else -1.0

    def evaluate(self, text: str) -> dict:
        """Full diagnostic breakdown, useful for logging/debugging."""

        pass


# --------------------------------------------------------------------------- #
# 2. Pluggable policy interface + REINFORCE trainer
# --------------------------------------------------------------------------- #

class PolicyInterface(Protocol):
    """Anything the trainer can sample from and update.

    Implement this against your real LLM (e.g. wrap HF `generate` +
    token log-probs, or an API-based sampler with a learnable proposal
    distribution) to do real RL fine-tuning.
    """

    def sample(self, prompt: str) -> Tuple[str, float]:
        """Return (completion_text, log_prob_of_that_completion)."""
        ...

    def update(self, prompt: str, completion: str, log_prob: float,
               advantage: float, lr: float) -> None:
        """Apply a policy-gradient update using the given advantage."""
        ...


@dataclass
class ReinforceTrainer:
    """
    Minimal REINFORCE loop:
        loss = -log_prob(completion) * advantage
        advantage = reward - baseline   (baseline = running mean reward)

    Works with any PolicyInterface, so it can drive real LLM fine-tuning
    once you supply a real policy wrapper.

    """
    reward_model: Optional[ReasoningRewardModel] = None
    reward_fn: Optional[Callable[[str, str], float]] = None
    lr: float = 0.05
    baseline_momentum: float = 0.9
    _baseline: float = field(default=0.0, init=False)

    def _score(self, prompt: str, completion: str) -> float:
        if self.reward_fn is not None:
            return self.reward_fn(prompt, completion)
        if self.reward_model is not None:
            return self.reward_model.compute_reward(prompt, completion)
        raise ValueError("Either reward_model or reward_fn must be provided.")

    def train_step(self, policy: PolicyInterface, prompt: str) -> dict:
        completion, log_prob = policy.sample(prompt)
        reward = self._score(prompt, completion)

        advantage = reward - self._baseline
        self._baseline = (self.baseline_momentum * self._baseline
                           + (1 - self.baseline_momentum) * reward)

        policy.update(prompt, completion, log_prob, advantage, self.lr)

        return {
            "prompt": prompt,
            "completion": completion,
            "reward": reward,
            "advantage": advantage,
            "baseline": self._baseline,
        }

    def train(self, policy: PolicyInterface, prompts: List[str],
              epochs: int = 1, verbose: bool = True) -> List[dict]:
        history = []
        for epoch in range(epochs):
            for prompt in prompts:
                log = self.train_step(policy, prompt)
                log["epoch"] = epoch
                history.append(log)
                if verbose:
                    print(f"[epoch {epoch}] reward={log['reward']:+.3f} "
                          f"baseline={log['baseline']:+.3f}  "
                          f"prompt={prompt!r} -> completion={log['completion']!r}")
        return history


class CoursePolicy:
    """
    Learnable multiclass policy over `CoursePolicy`'s 2 action classes.

    This plays the same structural role the old `BanditPolicy` played
    (per-prompt learnable logits, softmax sampling, REINFORCE update) but
    the action space is now the real 2-way course classification task
    instead of a hand-picked list of candidate completions:

      - `sample(title)`  -> (predicted_label: str, log_prob: float)
      - `update(...)`    -> REINFORCE / policy-gradient step on the logits

    Reward is supplied externally (see `gift_card_reward` /
    `CoursePolicy.get_ground_truth_action`) via `ReinforceTrainer`'s
    `reward_fn` hook, since it depends on comparing the *predicted* class
    against the title's *true* class -- not on the completion text alone.
    """

    # def __init__(self, titles: List[str], teacher: Optional[CoursePolicy] = None,
    def __init__(self, titles: List[str], seed: int = 0):        
        self.action_map = ACTIONS.CLASSES
        self.actions = list(self.action_map.keys())  # index -> label
        self.num_actions = len(self.action_map)

        self.logits = {title: [0.0] * self.num_actions for title in titles}
        self._rng = random.Random(seed)

    def _softmax(self, logits: List[float]) -> List[float]:
        m = max(logits)
        exps = [math.exp(x - m) for x in logits]
        s = sum(exps)
        return [e / s for e in exps]

    def sample(self, prompt: str) -> Tuple[str, float]:
        probs = self._softmax(self.logits[prompt])
        idx = self._rng.choices(range(len(probs)), weights=probs, k=1)[0]
        return self.actions[idx], math.log(probs[idx])

    def update(self, prompt: str, completion: str, log_prob: float,
               advantage: float, lr: float) -> None:
        probs = self._softmax(self.logits[prompt])
        idx = self.actions.index(completion)
        # Gradient of log softmax w.r.t. logits, scaled by advantage (REINFORCE)
        for i in range(len(self.logits[prompt])):
            grad = (1.0 if i == idx else 0.0) - probs[i]
            self.logits[prompt][i] += lr * advantage * grad


class CoursePolicyCompat:
    """Compatibility class for unpickling models saved from preprocessing.py."""

    def _ensure_prompt(self, prompt: str) -> None:
        if prompt not in self.logits:
            self.logits[prompt] = [0.0] * self.num_actions

    def _softmax(self, logits: list[float]) -> list[float]:
        m = max(logits)
        exps = [math.exp(x - m) for x in logits]
        total = sum(exps)
        return [e / total for e in exps]


class GiftCardPolicy(CoursePolicy):
    """Temporary class to serialize policies as GiftCardPolicy for backward compatibility."""
    def _ensure_prompt(self, prompt: str) -> None:
        if prompt not in self.logits:
            self.logits[prompt] = [0.0] * self.num_actions


class _PolicyUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        if (module == "__main__" or module == "parser") and name == "GiftCardPolicy":
            return CoursePolicyCompat
        return super().find_class(module, name)


_POLICY: CoursePolicyCompat | None = None


def _load_policy() -> CoursePolicyCompat:
    global _POLICY
    if _POLICY is not None:
        return _POLICY

    policy_path = Path("models/prediction_model.pkl")
    with policy_path.open("rb") as fp:
        _POLICY = _PolicyUnpickler(fp).load()
    return _POLICY


# --------------------------------------------------------------------------- #
# Demo / self-test
# --------------------------------------------------------------------------- #


def parse_raw_data(raw_data):

    print("=== REINFORCE demo (CoursePolicy, multiclass) ===")

    courses = parse_raw_video_data(raw_data)

    reward_model = ReasoningRewardModel() 
    
    policy = _load_policy()
    parsed_results = []
    cat1_count = 0
    cat2_count = 0
    for course_name in courses:
        # title = item['title']
        # print(title)
        # course_info = parse_title(title)
        # if course_info is None:
        #     continue
        # course_name = course_info['course']

        policy._ensure_prompt(course_name)
        probs = policy._softmax(policy.logits[course_name])
        pred_idx = max(range(len(probs)), key=lambda i: probs[i])
        pred_label = policy.actions[pred_idx]
        true_idx = reward_model.get_ground_truth_action(course_name)
        true_label = reward_model.actions[true_idx]
        match = "OK" if pred_idx == true_idx else "MISS"
        print(f"  [{match}] p={probs[pred_idx]:.3f}  pred={pred_label:8s} "
              f"true={true_label:8s}  title={course_name!r}")
        parsed_item = {'title':course_name, 'category':pred_label}
        parsed_results.append(parsed_item)

        if pred_idx == 0:
            cat1_count += 1
        else:
            cat2_count += 1

    return parsed_results, cat1_count, cat2_count

from langchain_google_genai import ChatGoogleGenerativeAI
import os
    
remote_llm = ChatGoogleGenerativeAI(
    model="gemma-4-26b-a4b-it",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.1,
    max_output_tokens=4096
)

def parse_semantic_data(raw_data):
    prompt = """You are a precise classifier. Rephrase the input course name to fit the category "Generative AI, Frontier Models & Strategy".
Output ONLY the final rephrased title. No quotes, no intro, no explanation.

Input: Stanford CME295 Transformers & LLMs
Output: Transformers & LLMs

Input: Stanford CME296 Diffusion & Large Vision Models
Output: Diffusion & Large Vision Models

Input: Stanford CS336 Language Modeling from Scratch
Output: Language Modeling from Scratch

Input: Stanford MS&E435 Economics of the AI Supercycle
Output: Economics of the AI Supercycle

Input: {text}
Output:"""



    print("=== REINFORCE demo (CoursePolicy, multiclass) ===")

    courses = parse_raw_video_data(raw_data)

    reward_model = ReasoningRewardModel() 
    
    policy = _load_policy()
    parsed_results = []
    cat1_count = 0
    cat2_count = 0
    for course_name in courses:
        # title = item['title']
        # print(title)
        # course_info = parse_title(title)
        # if course_info is None:
        #     continue
        # course_name = course_info['course']

        policy._ensure_prompt(course_name)
        probs = policy._softmax(policy.logits[course_name])
        pred_idx = max(range(len(probs)), key=lambda i: probs[i])
        pred_label = policy.actions[pred_idx]
        print(course_name, pred_label)
        if pred_idx == 1:
            response = remote_llm.invoke(prompt.format(text=course_name))
            if isinstance(response.content, list):
                new_course_name = "".join([part.get("text", "") for part in response.content if part.get("type") == "text"]).strip()
            else:
                new_course_name = response.content.strip()
            print("New course name: ", new_course_name)
            
            if not new_course_name:
                print(f"  [WARN] LLM returned empty response for '{course_name}', keeping original label.")
            else:
                policy._ensure_prompt(new_course_name)
                probs = policy._softmax(policy.logits[new_course_name])
                pred_idx = max(range(len(probs)), key=lambda i: probs[i])
                pred_label = policy.actions[pred_idx]

        parsed_item = {'title':course_name, 'category':pred_label}
        parsed_results.append(parsed_item)

        if pred_idx == 0:
            cat1_count += 1
        else:
            cat2_count += 1

    return parsed_results, cat1_count, cat2_count

