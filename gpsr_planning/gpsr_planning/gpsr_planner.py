#!/usr/bin/env python3

# MIT License

# Copyright (c) 2023  Miguel Ángel González Santamarta

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
from typing import Tuple
from llama_ros.langchain import ChatLlamaROS
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
import datetime as dt
import re
from itertools import product

class GpsrPlanner:

    def __init__(
        self,
        robot_actions_path: str = "robot_actions.json",
        waypoints_path: str = "waypoints.json",
        objects_path: str = "objects.json",
        names_path: str = "names.json",
        nfr_profiles_path: str = "src/GPSR_planning/gpsr_planning/params/nfr_profiles.json"
    ) -> None:

        self.robot_actions = json.load(open(robot_actions_path))
        self.waypoints_path = waypoints_path

        self.create_grammar()

        # Load NFR profiles (single "Constraints" list)
        self.nfr_profiles = json.load(open(nfr_profiles_path))["profiles"]

        self.llm = ChatLlamaROS(
            temp=0.60,
            grammar_schema=self.grammar_schema
        )

        is_lora_added = False

        self.actions_descriptions = ""
        for robot_act in self.robot_actions:
            self.actions_descriptions += f"- {robot_act['name']}: {robot_act['description']}\n"

        # Monolithic prompt with clear NFR usage instruction
        monolithic_prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "You are a robot named Tiago participating in the Robocup with the Gentlebots team from Spain, "
                "made up of the Rey Juan Carlos University of Madrid and the University of León. "

                "Generate a plan as a sequence of actions to achieve the goal. "
                "First, decide the necessary actions using ONLY the actions listed below. "
                "Do not invent new actions or parameters. "

                "After deciding the actions, consider ONLY the NFR profiles that match the action names you chose. "
                "Use those NFR as guidance to slightly improve the plan if helpful — for example by making an explanation more precise or by adding a small check/fallback. "

                "Rules: "
                "- Never change the core actions or their parameters unless absolutely necessary. "
                "- Keep explanations short, impersonal, and concise. "
                "- If no relevant NFR or no meaningful improvement is possible, output the plan exactly as decided. "

                "Output ONLY a valid JSON object with a key 'actions' containing a list of actions. "
                "Each action must have 'explanation_of_next_actions' and one action-specific key with parameters. "
                "No additional text outside the JSON. "

                "Actions are performed at waypoints. Move to waypoints as needed. "
                "Rooms, furniture and tables are waypoints — no need to find them. "
                "Today is {day}, tomorrow is {tomorrow} and the time is {time_h}. "
                "\n\n"

                "AVAILABLE ACTIONS:\n"
                "{actions_descriptions}\n\n"

                "NFR PROFILES (consider only those matching your chosen actions):\n"
                "{nfr_full_summary}"
            ),
            HumanMessagePromptTemplate.from_template(
                "You are at the instruction point. Generate a plan to achieve this goal: {prompt}"
            )
        ])

        self.chain = monolithic_prompt_template | self.llm | StrOutputParser()

    def cancel(self) -> None:
        self.llm.cancel()

    def send_prompt(self, prompt: str) -> Tuple[dict | str]:

        prompt = prompt + " "
        prompt = re.sub(r'\b(?:tell|say)\s+me\b', lambda match: match.group(0).replace("me", "at the instruction point"), prompt, flags=re.IGNORECASE)
        prompt = prompt.replace("to to", "to").replace("them", "him").strip()

        today_dt = dt.datetime.now()
        day_suffix = lambda day: 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
        day = today_dt.strftime(f"%A {today_dt.day}{day_suffix(today_dt.day)}")

        time_h = today_dt.strftime("%H:%M")
        tomorrow = (today_dt + dt.timedelta(days=1)).strftime("%A")

        # Build full NFR summary (SLM is instructed to filter it internally)
        nfr_full_summary = ""
        for profile in self.nfr_profiles:
            constraints = "; ".join(profile.get('Constraints', []))
            nfr_full_summary += f"- {profile['name']}: {constraints}\n"

        response = self.chain.invoke({
            "prompt": prompt,
            "actions_descriptions": self.actions_descriptions[:-1],
            "nfr_full_summary": nfr_full_summary,
            "day": day,
            "tomorrow": tomorrow,
            "time_h": time_h
        })

        print("LLM Response:", response)

        try:
            plan = json.loads(response)
            return plan, prompt
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print("Raw response was:", response[:500] + "..." if len(response) > 500 else response)
            return {"actions": []}, prompt

    def create_grammar(self) -> None:
        self.actions_descriptions = ""
        actions_refs = []
        for robot_act in self.robot_actions:
            self.actions_descriptions += f"- {robot_act['name']}: {robot_act['description']}\n"
            actions_refs.append({"$ref": f"#/definitions/{robot_act['name']}"})

        action_definitions = {}
        for robot_act in self.robot_actions:
            action_args = {"type": "object", "properties": {}, "required": []}

            if robot_act['arg_case'] == 'allOf' and len(robot_act['args'].keys()) != 0:
                for arg in robot_act["args"]:
                    action_args['properties'][arg] = {"type": robot_act["args"][arg]["type"]}
                    action_args['required'].append(arg)
                    if "choices" in robot_act["args"][arg]:
                        action_args["properties"][arg]["enum"] = robot_act["args"][arg]["choices"]

            elif robot_act['arg_case'] == 'anyOf' and robot_act['name'] == 'find_object':
                action_args['oneOf'] = []
                item_list = {'item': ['category', 'specific_item'], 'category': ['category'], 'none': []}
                size_list = ['size', 'weight']
                args_obj = {}
                for arg in robot_act["args"]:
                    args_obj[arg] = {"type": robot_act["args"][arg]["type"], "enum": robot_act["args"][arg]["choices"]}

                for item, size in product(list(item_list.keys()), size_list):
                    action_args['oneOf'].append({
                        "properties": {k: args_obj[k] for k in [*item_list[item], size]},
                        "required": item_list[item]
                    })

            elif robot_act['arg_case'] == 'anyOf':
                for arg in robot_act["args"]:
                    action_args['properties'][arg] = {"type": robot_act["args"][arg]["type"]}
                    if "choices" in robot_act["args"][arg]:
                        action_args["properties"][arg]["enum"] = robot_act["args"][arg]["choices"]

            elif robot_act['arg_case'] == 'oneOf':
                action_args['oneOf'] = []
                del action_args['properties']
                del action_args['required']

                for search_by_option in robot_act['args']['search_by']['choices']:
                    option_obj = {
                        "properties": {"search_by": {"const": search_by_option}},
                        "required": ['search_by']
                    }

                    if search_by_option != 'none':
                        option_obj['properties'][search_by_option] = {
                            'type': robot_act['args'][search_by_option]['type'],
                            'enum': robot_act['args'][search_by_option]['choices']
                        }

                    if 'previously_found' in robot_act['args']:
                        option_obj["properties"]['previously_found'] = {'type': 'boolean'}
                        option_obj['required'].append(search_by_option)

                    action_args['oneOf'].append(option_obj)

            action_def = {
                "type": "object",
                "properties": {
                    "explanation_of_next_actions": {"type": "string", "maxLength": 200},
                    robot_act['name']: action_args
                },
                "required": ['explanation_of_next_actions', robot_act['name']]
            }

            action_definitions[robot_act["name"]] = action_def

        self.grammar_schema = json.dumps({
            "definitions": action_definitions,
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "items": {"type": "object", "anyOf": actions_refs},
                    "minItems": 1,
                    "maxItems": 15
                }
            },
            "required": ["actions"]
        })