import json
import re
import time
import statistics
import operator
import os
import shutil
import csv
from typing import Tuple, List, Dict, Any, Optional

class QUData:
    def __init__(self, template_path: str, questionnaire_file_path: str, output_path: str, experiment: str, name: str):
        self.template_path = template_path
        self.questionnaire_file_path = questionnaire_file_path
        self.output_path = output_path
        self.experiment = experiment
        self.name = name

        os.makedirs(self.output_path, exist_ok=True)

        shutil.copy(self.template_path, self.questionnaire_file_path)

        self.data = self.load_data()

    def load_data(self):
        with open(self.questionnaire_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_data(self) -> None:
        with open(self.questionnaire_file_path, 'w', encoding='utf-8') as file:
            json.dump(self.data, file, indent=2, ensure_ascii=False)
        
        self.update_template()

    def update_template(self):
        template_data = self.load_template()
        
        template_data['questionnaires'] = template_data['questionnaires'][:len(self.data['questionnaires'])]
        while len(template_data['questionnaires']) < len(self.data['questionnaires']):
            template_data['questionnaires'].append({})

        for q_template, q_current in zip(template_data['questionnaires'], self.data['questionnaires']):
            self.update_questionnaire_excluding_selected(q_template, q_current)
        
        with open(self.template_path, 'w', encoding='utf-8') as file:
            json.dump(template_data, file, indent=2, ensure_ascii=False)

    def load_template(self):
        with open(self.template_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def update_questionnaire_excluding_selected(self, q_template, q_current):
        for key, value in q_current.items():
            if key != 'components':
                q_template[key] = value
            else:
                q_template['components'] = []
                for c_current in q_current['components']:
                    c_template = {}
                    for k, v in c_current.items():
                        if k != 'options':
                            c_template[k] = v
                        else:
                            c_template['options'] = []
                            for opt_current in c_current['options']:
                                opt_template = {k: v for k, v in opt_current.items() if k != 'selected'}
                                c_template['options'].append(opt_template)
                    q_template['components'].append(c_template)

    def add_questionnaire(self, questionnaire: Dict[str, Any]) -> None:
        self.data['questionnaires'].append(questionnaire)
        self.save_data()

    def delete_questionnaire(self, questionnaire_id: str) -> bool:
        initial_length = len(self.data['questionnaires'])
        self.data['questionnaires'] = [q for q in self.data['questionnaires'] if q['id'] != questionnaire_id]
        if len(self.data['questionnaires']) < initial_length:
            self.save_data()
            return True
        return False

    def update_questionnaire(self, questionnaire_id: str, updated_questionnaire: Dict[str, Any]) -> bool:
        for i, q in enumerate(self.data['questionnaires']):
            if q['id'] == questionnaire_id:
                self.data['questionnaires'][i] = updated_questionnaire
                self.save_data()
                return True
        return False

    def get_questionnaire(self, questionnaire_id: str) -> Optional[Dict[str, Any]]:
        for questionnaire in self.data['questionnaires']:
            if questionnaire['id'] == questionnaire_id:
                return questionnaire
        return None

    def get_all_questionnaire_ids(self) -> List[str]:
        return [q['id'] for q in self.data['questionnaires']]

    def get_labeled_values(self, questionnaire: Dict[str, Any], label: str) -> List[float]:
        values = []
        for component in questionnaire['components']:
            if component['type'] == 'single_choice' and component.get('label') == label:
                selected_value = next((opt['value'] for opt in component['options'] if opt.get('selected')), None)
                if selected_value is not None:
                    values.append(selected_value)
        return values

    def calculate_variable(self, questionnaire_id: str, variable_name: str) -> Optional[float]:
        questionnaire = self.get_questionnaire(questionnaire_id)
        if not questionnaire:
            return None

        for variable in questionnaire.get('variables', []):
            if variable['name'] == variable_name:
                return self.parse_and_calculate(questionnaire, variable['calculation'])

        return None

    def parse_and_calculate(self, questionnaire: Dict[str, Any], calculation: str) -> float:
        def replace_function(match):
            func = match.group(1)
            label = match.group(2)
            values = self.get_labeled_values(questionnaire, label)
            
            if not values:
                return '0'
            
            if func == 'sum':
                return str(sum(values))
            elif func == 'mean':
                return str(statistics.mean(values))
            elif func == 'std':
                return str(statistics.stdev(values)) if len(values) > 1 else '0'
            elif func == 'var':
                return str(statistics.variance(values)) if len(values) > 1 else '0'
            elif func == 'median':
                return str(statistics.median(values))
            elif func == 'min':
                return str(min(values))
            elif func == 'max':
                return str(max(values))
            else:
                return '0'

        pattern = r'(sum|mean|std|var|median|min|max)\[(\w+)\]'
        calculation = re.sub(pattern, replace_function, calculation)
        
        def compare_function(match):
            left = float(match.group(1))
            op = match.group(2)
            right = float(match.group(3))
            
            ops = {'>': operator.gt, '<': operator.lt, '>=': operator.ge, 
                   '<=': operator.le, '==': operator.eq, '!=': operator.ne}
            
            result = ops[op](left, right)
            return str(int(result))

        comparison_pattern = r'(\d+(?:\.\d+)?)\s*(>|<|>=|<=|==|!=)\s*(\d+(?:\.\d+)?)'
        calculation = re.sub(comparison_pattern, compare_function, calculation)
        
        return eval(calculation)

    def analyze_questionnaire(self, questionnaire_id: str) -> Dict[str, Any]:
        questionnaire = self.get_questionnaire(questionnaire_id)
        if not questionnaire:
            return {}

        results = {}
        for variable in questionnaire.get('variables', []):
            variable_name = variable['name']
            value = self.calculate_variable(questionnaire_id, variable_name)
            results[variable_name] = value

        return results

    def get_questionnaire_components(self, questionnaire_id: str) -> List[Dict[str, Any]]:
        questionnaire = self.get_questionnaire(questionnaire_id)
        return questionnaire['components'] if questionnaire else []

    def update_questionnaire_component(self, questionnaire_id: str, component_index: int, updated_component: Dict[str, Any]) -> bool:
        questionnaire = self.get_questionnaire(questionnaire_id)
        if questionnaire and 0 <= component_index < len(questionnaire['components']):
            questionnaire['components'][component_index] = updated_component
            self.save_data()
            return True
        return False

    def questionnaire_to_custom_syntax(self, questionnaire: Dict[str, Any]) -> str:
        if questionnaire is None:
            return ""
        
        lines = []
        lines.append(f"Name: {questionnaire.get('id', '')}")
        lines.append(f"Title: {questionnaire.get('title', '')}")
        
        for component in questionnaire.get('components', []):
            if component['type'] == 'instruction':
                lines.append(f"Instruction: {component.get('content', '')}")
            elif component['type'] in ['single_choice', 'multiple_choice']:
                lines.append("Single Choice" if component['type'] == 'single_choice' else "Multiple Choice")
                lines.append(f"Title: {component.get('content', '')}")
                lines.append(f"Label: {component.get('label', '')}")
                options = ''.join([f"[{opt['text']}]" for opt in component.get('options', [])])
                values = ''.join([f"[{opt['value']}]" for opt in component.get('options', [])])
                lines.append(f"Options: {options}")
                lines.append(f"Values: {values}")
            elif component['type'] == 'text_input':
                lines.append("Text Input")
                lines.append(f"Title: {component.get('content', '')}")

        if questionnaire.get('variables'):
            lines.append("Variables")
            for var in questionnaire['variables']:
                lines.append(f"Name: {var.get('name', '')}")
                lines.append(f"Formula: {var.get('calculation', '')}")

        return '\n'.join(lines)

    def analyze_specific_questionnaire(self, questionnaire_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        questionnaire = self.get_questionnaire(questionnaire_id)
        if not questionnaire:
            return [], {}

        answers = []
        results = {}

        for component in questionnaire.get('components', []):
            if component['type'] in ['single_choice', 'multiple_choice']:
                answer = {
                    'question': component['content'],
                    'label': component.get('label', ''),
                    'answer': [opt['text'] for opt in component['options'] if opt.get('selected')]
                }
                answers.append(answer)
            elif component['type'] == 'text_input':
                answer = {
                    'question': component['content'],
                    'answer': component.get('answer', '')
                }
                answers.append(answer)

        for variable in questionnaire.get('variables', []):
            variable_name = variable['name']
            value = self.calculate_variable(questionnaire_id, variable_name)
            results[variable_name] = value

        return answers, results

    def save_questionnaire_results(self, questionnaire_id: str, answers: List[Dict[str, Any]], results: Dict[str, Any]):
        answers_file = os.path.join(self.output_path, f'{self.experiment}_{self.name}_{questionnaire_id}_答题记录.csv')
        with open(answers_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ['Question', 'Answer']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for answer in answers:
                # writer.writerow({
                # })
                writer.writerow({
                    'Question': answer['question'],
                    'Answer': answer['answer'] if isinstance(answer['answer'], str) else ', '.join(answer['answer'])
                })

        results_file = os.path.join(self.output_path, f'{self.experiment}_{self.name}_{questionnaire_id}_Variable.csv')
        with open(results_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Variable', 'Value'])
            for variable, value in results.items():
                writer.writerow([variable, value])

        return answers_file, results_file

    def custom_syntax_to_questionnaire(self, syntax: str) -> Optional[Dict[str, Any]]:
        lines = syntax.split('\n')
        questionnaire = {"id": "", "title": "", "components": [], "variables": []}
        current_component = None
        mode = None
        option_texts = []
        option_values = []
        var_name = None

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            if line.startswith("Name:"):
                if mode != "Variable":
                    questionnaire["id"] = line.replace("Name:", "").strip().replace('"', '\\"')
                else:
                    var_name = line.replace("Name:", "").strip().replace('"', '\\"')
            elif line.startswith("Title:"):
                if mode is None:
                    questionnaire["title"] = line.replace("Title:", "").strip().replace('"', '\\"')
                elif current_component:
                    current_component["content"] = line.replace("Title:", "").strip().replace('"', '\\"')
                    if mode == "Text Input":
                        questionnaire["components"].append(current_component)
                        current_component = None
                        mode = None
            elif line.startswith("Instruction:"):
                questionnaire["components"].append({
                    "type": "instruction",
                    "content": line.replace("Instruction:", "").strip().replace('"', '\\"')
                })
            elif line in ["Single Choice", "Multiple Choice"]:
                if current_component:
                    questionnaire["components"].append(current_component)
                mode = line
                # current_component = {
                #     "content": "",
                #     "label": "",
                #     "options": []
                # }
                current_component = {
                    "type": "single_choice" if mode == "Single Choice" else "multiple_choice",
                    "content": "",
                    "label": "",
                    "options": []
                }
            elif line == "Text Input":
                if current_component:
                    questionnaire["components"].append(current_component)
                mode = "Text Input"
                current_component = {"type": "text_input", "content": ""}
            elif line.startswith("Label:"):
                if current_component and mode != "Text Input":
                    current_component["label"] = line.replace("Label:", "").strip().replace('"', '\\"')
            elif line.startswith("Options:"):
                options = re.findall(r'\[(.*?)\]', line)
                if not options:
                    raise ValueError(f"Failed To Parse Options At Line {line_num}.")
                option_texts = options
            elif line.startswith("Values:"):
                values = re.findall(r'\[(\d+)\]', line)
                if not values:
                    raise ValueError(f"Failed To Parse Values At Line {line_num}.")
                option_values = [int(v) for v in values]
                if current_component and len(option_texts) == len(option_values):
                    for text, value in zip(option_texts, option_values):
                        current_component["options"].append({"text": text.replace('"', '\\"'), "value": value})
                    questionnaire["components"].append(current_component)
                    current_component = None
                    mode = None
                else:
                    raise ValueError(f"Number Of Options Does Not Match Number Of Values At Line {line_num}.")
            elif line == "Variables":
                if current_component:
                    questionnaire["components"].append(current_component)
                mode = "Variable"
                current_component = None
            elif line.startswith("Formula:"):
                if mode == "Variable":
                    if var_name is None:
                        raise ValueError(f"Variable Formula Missing Name Definition At Line {line_num}.")
                    var_formula = line.replace("Formula:", "").strip().replace('"', '\\"')
                    questionnaire["variables"].append({"name": var_name, "calculation": var_formula})
                    var_name = None
                else:
                    raise ValueError(f"Formula Line Appears In Non-variable Mode At Line {line_num}.")
            else:
                raise ValueError(f"Unknown Syntax In Line: '{line}' At Line {line_num}.")

        if current_component:
            questionnaire["components"].append(current_component)

        if not questionnaire["id"]:
            raise ValueError("Questionnaire is missing an ID.")
        if not questionnaire["title"]:
            raise ValueError("Questionnaire is missing a title.")

        return questionnaire

    def refresh_questionnaire_list(self) -> List[Dict[str, str]]:
        
        return [{"id": q["id"], "title": q["title"]} for q in self.data["questionnaires"]]

    def sync_template(self):
        
        self.update_template()