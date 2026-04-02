from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QListWidgetItem, QStackedWidget, QMessageBox, QLabel, QButtonGroup
from qfluentwidgets import (SubtitleLabel, StrongBodyLabel, FluentStyleSheet, ListWidget, Pivot, 
                            CardWidget, LineEdit, BodyLabel, PushButton, 
                            TextEdit, ComboBox, CheckBox, SmoothScrollArea, RadioButton,
                            PrimaryPushButton, InfoBar, InfoBarPosition)
from .gallery_interface import GalleryInterface
from ..data.qu_data import QUData
from .radio_option import RadioOption  
from .check_option import CheckOption  
import json
from ..common.translator import Translator
import csv
import os
import uuid

class QUInterface(GalleryInterface):
    def __init__(self, parent, template_path: str, questionnaire_file_path: str, output_path: str, experiment: str, name: str):
        t = Translator()
        super().__init__(
            title='',
            subtitle='',
            parent=parent
        )
        self.setObjectName('QUInterface')

        self.experiment = experiment
        self.name = name

        self.qu_data = QUData(template_path=template_path, questionnaire_file_path=questionnaire_file_path, output_path=output_path, experiment=experiment, name=name)
        self.single_choice_button_groups = []
        self.multiple_choice_groups = []
        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        # Left column
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)

        questionnaire_label = StrongBodyLabel("Questionnaires", self)
        left_layout.addWidget(questionnaire_label)
        # Add experiment info display
        self.setup_experiment_info(left_layout)

        # Add and delete questionnaire buttons
        button_layout = QHBoxLayout()
        self.add_questionnaire_button = PrimaryPushButton("New Questionnaire", self)
        self.add_questionnaire_button.setFixedHeight(40)
        self.add_questionnaire_button.clicked.connect(self.add_new_questionnaire)
        button_layout.addWidget(self.add_questionnaire_button)

        self.delete_questionnaire_button = PushButton("Delete", self)
        self.delete_questionnaire_button.setFixedHeight(40)
        self.delete_questionnaire_button.clicked.connect(self.delete_current_questionnaire)
        button_layout.addWidget(self.delete_questionnaire_button)

        left_layout.addLayout(button_layout)

        # Questionnaire list
        questionnaire_card = CardWidget(self)
        # questionnaire_card.setStyleSheet("background-color: #323232;")
        # questionnaire_card.setStyleSheet("background-color: #263544;")
        questionnaire_card.setStyleSheet("background-color: #f5f0ff;")
        card_layout = QVBoxLayout(questionnaire_card)
        card_layout.setContentsMargins(5, 5, 5, 5)
        card_layout.setSpacing(30)
        self.questionnaire_list = ListWidget(self)
        self.questionnaire_list.itemClicked.connect(self.on_questionnaire_selected)
        card_layout.addWidget(self.questionnaire_list)

        left_layout.addWidget(questionnaire_card)
        main_layout.addWidget(left_column, 1)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        self.pivot = Pivot(self)
        self.pivot.addItem(routeKey='answer', icon=None, text='Answer Mode', onClick=self.show_answer_mode)
        self.pivot.addItem(routeKey='edit', icon=None, text='Edit Mode', onClick=self.show_edit_mode)
        right_layout.addWidget(self.pivot)

        self.stacked_widget = QStackedWidget(self)
        self.edit_widget = TextEdit(self)
        self.answer_widget = SmoothScrollArea(self)
        self.answer_widget.enableTransparentBackground()
        self.answer_content = QWidget()
        self.answer_content.setObjectName('view')
        
        self.answer_layout = QVBoxLayout(self.answer_content)
        self.answer_widget.setWidget(self.answer_content)
        self.answer_widget.setWidgetResizable(True)

        self.stacked_widget.addWidget(self.edit_widget)
        self.stacked_widget.addWidget(self.answer_widget)
        right_layout.addWidget(self.stacked_widget)

        self.edit_buttons_widget = QWidget(self)  
        self.edit_buttons_layout = QHBoxLayout(self.edit_buttons_widget)
        self.reset_button = PushButton("Reset", self)
        self.reset_button.setFixedHeight(40)
        self.reset_button.clicked.connect(self.reset_edit_content)
        self.confirm_button = PrimaryPushButton("Confirm", self)
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.clicked.connect(self.confirm_edit_content)
        self.edit_buttons_layout.addStretch(1)
        self.edit_buttons_layout.addWidget(self.reset_button)
        self.edit_buttons_layout.addWidget(self.confirm_button)
        right_layout.addWidget(self.edit_buttons_widget)

        main_layout.addWidget(right_column, 4)

        self.load_questionnaires()

        self.show_answer_mode()

    def setup_experiment_info(self, layout):
        info_card = CardWidget(self)
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(15, 15, 15, 15)

        experiment_label = BodyLabel(f"Experiment: {self.experiment}", self)
        name_label = BodyLabel(f"Participant: {self.name}", self)

        info_layout.addWidget(experiment_label)
        info_layout.addWidget(name_label)

        layout.addWidget(info_card)

    def load_questionnaires(self):
        self.questionnaire_list.clear()
        questionnaire_ids = self.qu_data.get_all_questionnaire_ids()
        for questionnaire_id in questionnaire_ids:
            item = QListWidgetItem(questionnaire_id)
            self.questionnaire_list.addItem(item)
        
        if self.questionnaire_list.count() > 0 and not self.questionnaire_list.currentItem():
            self.questionnaire_list.setCurrentRow(0)
            self.on_questionnaire_selected(self.questionnaire_list.item(0))

    def add_new_questionnaire(self):
        unique_id = str(uuid.uuid4())[:8]  
        # new_questionnaire = {
        #     "components": [],
        #     "variables": []
        # }
        new_questionnaire = {
            "id": f"NewQuestionnaire_{unique_id}",
            "title": "NewQuestionnaire",
            "components": [],
            "variables": []
        }
        self.qu_data.add_questionnaire(new_questionnaire)
        self.load_questionnaires()
        
        new_item = self.questionnaire_list.findItems(new_questionnaire["id"], Qt.MatchExactly)[0]
        self.questionnaire_list.setCurrentItem(new_item)
        self.on_questionnaire_selected(new_item)

    def delete_current_questionnaire(self):
        current_item = self.questionnaire_list.currentItem()
        if current_item is None:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content="Please Choose At Least One Questionnaire",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        questionnaire_id = current_item.text()
        self.qu_data.delete_questionnaire(questionnaire_id)
        self.load_questionnaires()

        if self.questionnaire_list.count() > 0:
            self.questionnaire_list.setCurrentRow(0)
            self.on_questionnaire_selected(self.questionnaire_list.item(0))
        else:
            self.clear_content()

    def on_questionnaire_selected(self, item):
        questionnaire_id = item.text()
        questionnaire = self.qu_data.get_questionnaire(questionnaire_id)
        self.current_questionnaire = questionnaire
        self.update_content()

    def update_content(self):
        custom_syntax = self.qu_data.questionnaire_to_custom_syntax(self.current_questionnaire)
        self.edit_widget.setPlainText(custom_syntax)

        self.clear_answer_layout()

        self.add_questionnaire_title_card(self.current_questionnaire['title'])

        for component in self.current_questionnaire['components']:
            if component['type'] == 'title':
                self.add_title_card(component)
            elif component['type'] == 'instruction':
                self.add_instruction_card(component)
            elif component['type'] == 'single_choice':
                self.add_single_choice_card(component)
            elif component['type'] == 'multiple_choice':
                self.add_multiple_choice_card(component)
            elif component['type'] == 'text_input':
                self.add_text_input_card(component)
        
        self.add_submit_button()

        self.answer_layout.addStretch(1)

    def create_card(self, content_widget):
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        card_layout.addWidget(content_widget)
        return card
    
    def add_questionnaire_title_card(self, title):
        title_label = SubtitleLabel(title, self)
        title_label.setWordWrap(True)  
        title_label.setAlignment(Qt.AlignCenter)  
        card = self.create_card(title_label)
        self.answer_layout.addWidget(card)

    def clear_answer_layout(self):
        while self.answer_layout.count():
            child = self.answer_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.single_choice_button_groups.clear()
        self.multiple_choice_groups.clear()

    def clear_content(self):
        self.edit_widget.clear()
        self.clear_answer_layout()

    def add_title_card(self, component):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = StrongBodyLabel(component['content'], self)
        title.setWordWrap(True)  
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  
        layout.addWidget(title)
        self.answer_layout.addWidget(card)

    def add_instruction_card(self, component):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        instruction = BodyLabel(component['content'], self)
        instruction.setWordWrap(True)  
        instruction.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  
        layout.addWidget(instruction)
        self.answer_layout.addWidget(card)

    def add_single_choice_card(self, component):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        question = BodyLabel(component['content'], self)
        question.setWordWrap(True)
        question.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(question)

        button_group = QButtonGroup(self)
        button_group.setExclusive(True)
        self.single_choice_button_groups.append(button_group)

        for option in component['options']:
            option_widget = RadioOption(option['text'], self)
            option_widget.radio.setChecked(option.get('selected', False))
            layout.addWidget(option_widget)
            button_group.addButton(option_widget.radio)

        self.answer_layout.addWidget(card)

    def add_multiple_choice_card(self, component):
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        question = BodyLabel(component['content'], self)
        question.setWordWrap(True)  
        question.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  
        layout.addWidget(question)

        checkboxes = []
        for option in component['options']:
            option_widget = CheckOption(option['text'], self)
            option_widget.checkbox.setChecked(option.get('selected', False))
            layout.addWidget(option_widget)
            checkboxes.append(option_widget.checkbox)

        self.multiple_choice_groups.append(checkboxes)
        self.answer_layout.addWidget(card)

    def add_text_input_card(self, component):
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        title = StrongBodyLabel(component['content'], self)
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        content_layout.addWidget(title)
        
        text_input = TextEdit(self)
        text_input.setPlaceholderText("Enter Your Response Here...")
        text_input.setAttribute(Qt.WA_InputMethodEnabled, True)
        
        text_input.setObjectName(f"text_input_{component['content']}")
        
        if 'answer' in component:
            text_input.setPlainText(component['answer'])
        
        text_input.setMinimumHeight(100)
        
        content_layout.addWidget(text_input)
        
        card = self.create_card(content_widget)
        self.answer_layout.addWidget(card)

    def add_submit_button(self):
        submit_card = CardWidget(self)
        layout = QVBoxLayout(submit_card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        submit_button = PrimaryPushButton("Submit", self)
        submit_button.setFixedHeight(40)
        submit_button.clicked.connect(self.submit_questionnaire)
        
        layout.addWidget(submit_button, alignment=Qt.AlignCenter)
        self.answer_layout.addWidget(submit_card)

    def submit_questionnaire(self):
        incomplete_questions = self.check_questionnaire_completion()
        if incomplete_questions:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=5000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Warning',
                content=f"The Following Questions Are Incomplete:\n" + "\n".join(incomplete_questions),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            return

        self.update_questionnaire_data()

        answers, results = self.qu_data.analyze_specific_questionnaire(self.current_questionnaire['id'])
        
        answers_file, results_file = self.qu_data.save_questionnaire_results(
            self.current_questionnaire['id'], 
            answers, 
            results
        )
        
        # InfoBar.success(
        #     orient=Qt.Horizontal,
        #     isClosable=True,
        #     position=InfoBarPosition.TOP,
        #     duration=5000,
        #     parent=self
        # )
        InfoBar.success(
            title='Success',
            content=f"Questionnaire Submitted Successfully. Responses Saved To {answers_file}, Results Saved To {results_file}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    def update_questionnaire_data(self):
        single_choice_index = 0
        multiple_choice_index = 0

        for component in self.current_questionnaire['components']:
            if component['type'] == 'single_choice':
                if single_choice_index < len(self.single_choice_button_groups):
                    button_group = self.single_choice_button_groups[single_choice_index]
                    for j, option in enumerate(component['options']):
                        option['selected'] = button_group.buttons()[j].isChecked()
                    single_choice_index += 1
            elif component['type'] == 'multiple_choice':
                if multiple_choice_index < len(self.multiple_choice_groups):
                    checkboxes = self.multiple_choice_groups[multiple_choice_index]
                    for j, option in enumerate(component['options']):
                        if j < len(checkboxes):
                            option['selected'] = checkboxes[j].isChecked()
                    multiple_choice_index += 1
            elif component['type'] == 'text_input':
                text_input = self.findChild(TextEdit, f"text_input_{component['content']}")
                if text_input:
                    component['answer'] = text_input.toPlainText()

        self.qu_data.update_questionnaire(self.current_questionnaire['id'], self.current_questionnaire)

    def show_edit_mode(self):
        self.stacked_widget.setCurrentWidget(self.edit_widget)
        self.edit_buttons_widget.show()  

    def show_answer_mode(self):
        self.stacked_widget.setCurrentWidget(self.answer_widget)
        self.edit_buttons_widget.hide()  

    def reset_edit_content(self):
        if self.current_questionnaire:
            custom_syntax = self.qu_data.questionnaire_to_custom_syntax(self.current_questionnaire)
            self.edit_widget.setPlainText(custom_syntax)
            # InfoBar.success(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=2000,
            #     parent=self
            # )
            InfoBar.success(
                title='Success',
                content="Content Has Been Reset",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def confirm_edit_content(self):
        syntax = self.edit_widget.toPlainText()
        try:
            updated_questionnaire = self.qu_data.custom_syntax_to_questionnaire(syntax)
            if not updated_questionnaire:
                raise ValueError("Conversion Failed. Please Check The Syntax Format.")
            
            if self.qu_data.update_questionnaire(self.current_questionnaire['id'], updated_questionnaire):
                self.current_questionnaire = updated_questionnaire
                self.update_content()
                
                current_item = self.questionnaire_list.currentItem()
                if current_item:
                    current_item.setText(updated_questionnaire['id'])
                
                # InfoBar.success(
                #     orient=Qt.Horizontal,
                #     isClosable=True,
                #     position=InfoBarPosition.TOP,
                #     duration=2000,
                #     parent=self
                # )
                InfoBar.success(
                    title='Success',
                    content="Questionnare Has Been Updated",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                raise ValueError("Failed To Update Questionnaire. The Specified Questionnaire ID May Not Exist.")
        except Exception as e:
            # InfoBar.warning(
            #     orient=Qt.Horizontal,
            #     isClosable=True,
            #     position=InfoBarPosition.TOP,
            #     duration=3000,
            #     parent=self
            # )
            InfoBar.warning(
                title='Error',
                content=f"Fail To Update：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def check_questionnaire_completion(self):
        incomplete_questions = []
        single_choice_index = 0
        multiple_choice_index = 0
        fill_in_blank_index = 0

        for component in self.current_questionnaire['components']:
            if component['type'] == 'single_choice':
                if single_choice_index < len(self.single_choice_button_groups):
                    button_group = self.single_choice_button_groups[single_choice_index]
                    if not any(button.isChecked() for button in button_group.buttons()):
                        incomplete_questions.append(component['content'])
                    single_choice_index += 1
                else:
                    incomplete_questions.append(component['content'])
            elif component['type'] == 'multiple_choice':
                if multiple_choice_index < len(self.multiple_choice_groups):
                    checkboxes = self.multiple_choice_groups[multiple_choice_index]
                    if not any(checkbox.isChecked() for checkbox in checkboxes):
                        incomplete_questions.append(component['content'])
                    multiple_choice_index += 1
                else:
                    incomplete_questions.append(component['content'])
            elif component['type'] == 'text_input':
                text_inputs = self.findChildren(TextEdit)
                if fill_in_blank_index < len(text_inputs):
                    text_input = text_inputs[fill_in_blank_index]
                    if not text_input.toPlainText().strip():
                        incomplete_questions.append(component['content'])
                    fill_in_blank_index += 1
                else:
                    incomplete_questions.append(component['content'])

        return incomplete_questions
