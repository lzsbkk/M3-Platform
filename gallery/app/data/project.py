import os
import sqlite3
import shutil
from typing import List, Dict, Any, Optional
import time

class Project:
    def __init__(self, project_name: str, base_path: str):
        self.project_name = project_name
        self.base_path = base_path
        self.project_path = os.path.join(base_path, project_name)
        self.db_path = os.path.join(self.project_path, f"{project_name}.db")

        self._create_project_structure()
        self._init_database()

    def _create_project_structure(self):
        
        if not os.path.exists(self.project_path):
            os.makedirs(self.project_path)

    def _init_database(self):
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            config_path TEXT,
            questionnaire_template_path TEXT
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY,
            experiment_id INTEGER,
            name TEXT NOT NULL,
            gender TEXT,
            age INTEGER,
            fnirs_data_path TEXT,
            fnirs_preprocessed_path TEXT,
            fnirs_output_path TEXT,
            eeg_data_path TEXT,
            eeg_montage_path TEXT,
            eeg_preprocessed_path TEXT,
            eeg_output_path TEXT,
            et_data_path TEXT,
            et_preprocessed_path TEXT,
            et_output_path TEXT,
            qu_data_path TEXT,
            qu_output_path TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id),
            UNIQUE(experiment_id, name)
        )
        ''')

        conn.commit()
        conn.close()

    def add_experiment(self, name: str) -> Optional[int]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        experiment_path = os.path.join(self.project_path, name)
        os.makedirs(experiment_path, exist_ok=True)

        config_src = os.path.join("resource", "config.json")
        config_dst = os.path.join(experiment_path, "config.json")
        template_src = os.path.join("resource", "Template.json")
        template_dst = os.path.join(experiment_path, "Template.json")

        shutil.copy(config_src, config_dst)
        shutil.copy(template_src, template_dst)

        config_rel_path = os.path.relpath(config_dst, self.project_path)
        template_rel_path = os.path.relpath(template_dst, self.project_path)

        try:
            cursor.execute("INSERT INTO experiments (name, config_path, questionnaire_template_path) VALUES (?, ?, ?)", 
                           (name, config_rel_path, template_rel_path))
            experiment_id = cursor.lastrowid
            conn.commit()
            return experiment_id
        except sqlite3.IntegrityError:
            print(f"Experiment '{name}' Already Exists")
            return None
        finally:
            conn.close()

    def create_output_folder(self, subject_id: int, data_type: str) -> str:
        
        subject = self.get_subject_data(subject_id)
        experiment = self.get_experiment_by_id(subject['experiment_id'])
        
        output_folder = os.path.join(self.project_path, experiment['name'], subject['name'], data_type, "Output")
        os.makedirs(output_folder, exist_ok=True)
        
        return os.path.relpath(output_folder, self.base_path)

    def remove_output_folder(self, subject_id: int, data_type: str):
        
        subject = self.get_subject_data(subject_id)
        output_path = subject.get(f'{data_type}_output_path')
        
        if output_path:
            full_path = os.path.join(self.base_path, output_path)
            if os.path.exists(full_path):
                shutil.rmtree(full_path)

    def get_experiment_by_id(self, experiment_id: int) -> Dict[str, Any]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM experiments WHERE id = ?", (experiment_id,))
            columns = [column[0] for column in cursor.description]
            values = cursor.fetchone()
            return dict(zip(columns, values)) if values else None
        finally:
            conn.close()

    def add_subject(self, experiment_id: int, name: str, gender: str, age: int, 
                    fnirs_data_path: Optional[str] = None, 
                    eeg_data_path: Optional[str] = None, 
                    eeg_montage_path: Optional[str] = None, 
                    et_data_path: Optional[str] = None) -> Optional[int]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM experiments WHERE id = ?", (experiment_id,))
        experiment_name = cursor.fetchone()[0]

        subject_path = os.path.join(self.project_path, experiment_name, name)
        os.makedirs(subject_path, exist_ok=True)

        subject_data = {
            "experiment_id": experiment_id,
            "name": name,
            "gender": gender,
            "age": age
        }

        if fnirs_data_path:
            # shutil.copy(fnirs_data_path, fnirs_data_dst)
            # subject_data["fnirs_data_path"] = os.path.relpath(fnirs_data_dst, self.base_path)
            fnirs_folder = os.path.join(subject_path, "fNIRS")
            os.makedirs(os.path.join(fnirs_folder, "Data"), exist_ok=True)
            fnirs_data_dst = os.path.join(fnirs_folder, "Data", os.path.basename(fnirs_data_path))
            shutil.copy(fnirs_data_path, fnirs_data_dst)
            subject_data["fnirs_data_path"] = os.path.relpath(fnirs_data_dst, self.base_path)
            subject_data["fnirs_output_path"] = os.path.relpath(os.path.join(fnirs_folder, "Output"), self.base_path)
            os.makedirs(os.path.join(fnirs_folder, "Output"), exist_ok=True)

        if eeg_data_path:
            # shutil.copy(eeg_data_path, eeg_data_dst)
            # subject_data["eeg_data_path"] = os.path.relpath(eeg_data_dst, self.base_path)

            # if eeg_montage_path:
            #     shutil.copy(eeg_montage_path, montage_dst)
            #     subject_data["eeg_montage_path"] = os.path.relpath(montage_dst, self.base_path)

            # if eeg_data_path.lower().endswith('.set'):
            #     fdt_file = os.path.splitext(eeg_data_path)[0] + '.fdt'
            #     if os.path.exists(fdt_file):
            #         shutil.copy(fdt_file, fdt_dst)

            # elif eeg_data_path.lower().endswith('.vhdr'):
            #     base_name = os.path.splitext(eeg_data_path)[0]
            #     for ext in ['.vmrk', '.eeg']:
            #         associated_file = base_name + ext
            #         if os.path.exists(associated_file):
            #             shutil.copy(associated_file, associated_dst)

            # elif eeg_data_path.lower().endswith('.edf'):
            #     shutil.copy(eeg_data_path, edf_dst)
            eeg_folder = os.path.join(subject_path, "EEG")
            os.makedirs(os.path.join(eeg_folder, "Data"), exist_ok=True)
            eeg_data_dst = os.path.join(eeg_folder, "Data", os.path.basename(eeg_data_path))
            shutil.copy(eeg_data_path, eeg_data_dst)
            subject_data["eeg_data_path"] = os.path.relpath(eeg_data_dst, self.base_path)
            subject_data["eeg_output_path"] = os.path.relpath(os.path.join(eeg_folder, "Output"), self.base_path)
            os.makedirs(os.path.join(eeg_folder, "Data"), exist_ok=True)

            if eeg_montage_path:
                montage_dst = os.path.join(eeg_folder, "Data", os.path.basename(eeg_montage_path))
                shutil.copy(eeg_montage_path, montage_dst)
                subject_data["eeg_montage_path"] = os.path.relpath(montage_dst, self.base_path)

            if eeg_data_path.lower().endswith('.set'):
                fdt_file = os.path.splitext(eeg_data_path)[0] + '.fdt'
                if os.path.exists(fdt_file):
                    fdt_dst = os.path.join(eeg_folder, "Data", os.path.basename(fdt_file))
                    shutil.copy(fdt_file, fdt_dst)

            elif eeg_data_path.lower().endswith('.vhdr'):
                base_name = os.path.splitext(eeg_data_path)[0]
                for ext in ['.vmrk', '.eeg']:
                    associated_file = base_name + ext
                    if os.path.exists(associated_file):
                        associated_dst = os.path.join(eeg_folder, "Data", os.path.basename(associated_file))
                        shutil.copy(associated_file, associated_dst)

            elif eeg_data_path.lower().endswith('.edf'):
                edf_dst = os.path.join(eeg_folder, "Data", os.path.basename(eeg_data_path))
                shutil.copy(eeg_data_path, edf_dst)

        if et_data_path:
            # shutil.copy(et_data_path, et_data_dst)
            # subject_data["et_data_path"] = os.path.relpath(et_data_dst, self.base_path)

            # if et_data_path.endswith(('.gz', '.csv', '.asc', '.edf')):
            #     et_src_dir = os.path.dirname(et_data_path)
            #     for item in os.listdir(et_src_dir):
            #         if item.endswith('.mp4') or item == 'meta':
            #             src_item = os.path.join(et_src_dir, item)
            #             if os.path.isdir(src_item):
            #                 shutil.copytree(src_item, dst_item)
            #             else:
            #                 shutil.copy(src_item, dst_item)
            et_folder = os.path.join(subject_path, "ET")
            os.makedirs(os.path.join(et_folder, "Data"), exist_ok=True)
            et_data_dst = os.path.join(et_folder, "Data", os.path.basename(et_data_path))
            shutil.copy(et_data_path, et_data_dst)
            subject_data["et_data_path"] = os.path.relpath(et_data_dst, self.base_path)
            subject_data["et_output_path"] = os.path.relpath(os.path.join(et_folder, "Output"), self.base_path)
            os.makedirs(os.path.join(et_folder, "Output"), exist_ok=True)

            if et_data_path.endswith(('.gz', '.csv', '.asc', '.edf')):
                et_src_dir = os.path.dirname(et_data_path)
                for item in os.listdir(et_src_dir):
                    if item.endswith('.mp4') or item == 'meta':
                        src_item = os.path.join(et_src_dir, item)
                        dst_item = os.path.join(et_folder, "Data", item)
                        if os.path.isdir(src_item):
                            shutil.copytree(src_item, dst_item)
                        else:
                            shutil.copy(src_item, dst_item)

        # qu_data_file = f"{experiment_name}_{name}.json"
        qu_folder = os.path.join(subject_path, "Questionnaire")
        os.makedirs(os.path.join(qu_folder, "Data"), exist_ok=True)
        qu_data_file = f"{experiment_name}_{name}.json"
        qu_data_path = os.path.join(qu_folder, "Data", qu_data_file)
        with open(qu_data_path, 'w') as f:
            f.write("{}")  
        subject_data["qu_data_path"] = os.path.relpath(qu_data_path, self.base_path)
        subject_data["qu_output_path"] = os.path.relpath(os.path.join(qu_folder, "Output"), self.base_path)
        os.makedirs(os.path.join(qu_folder, "Output"), exist_ok=True)

        columns = ", ".join(subject_data.keys())
        placeholders = ", ".join(["?" for _ in subject_data])
        values = tuple(subject_data.values())

        try:
            cursor.execute(f"INSERT INTO subjects ({columns}) VALUES ({placeholders})", values)
            subject_id = cursor.lastrowid
            conn.commit()
            return subject_id
        except sqlite3.IntegrityError:
            print(f"Participant '{name}' Already Exists In the Experiment.")
            return None
        finally:
            conn.close()

    def get_experiments(self) -> List[Dict[str, Any]]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, config_path, questionnaire_template_path FROM experiments")
        experiments = [{"id": row[0], "name": row[1], "config_path": row[2], "questionnaire_template_path": row[3]} for row in cursor.fetchall()]

        conn.close()
        return experiments

    def get_subjects(self, experiment_id: int) -> List[Dict[str, Any]]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM subjects WHERE experiment_id = ?", (experiment_id,))
        columns = [column[0] for column in cursor.description]
        subjects = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return subjects

    def get_experiment_name(self, experiment_id: int) -> str:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM experiments WHERE id = ?", (experiment_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def update_subject(self, subject_id: int, **kwargs) -> bool:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            current_subject = self.get_subject_data(subject_id)
            if not current_subject:
                print(f"Can't Find Participant of ID {subject_id}")
                return False

            experiment_name = self.get_experiment_name(current_subject['experiment_id'])
            subject_base_path = os.path.join(self.project_path, experiment_name, current_subject['name'])

            updates = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['fnirs_data_path', 'eeg_data_path', 'eeg_montage_path', 'et_data_path']:
                    if value:  
                        data_type = key.split('_')[0]  
                        
                        # data_folder = os.path.join(subject_base_path, {
                        data_folder = os.path.join(subject_base_path, {
                            'fnirs': 'fNIRS',
                            'eeg': 'EEG',
                            'et': 'ET'
                        }[data_type], "Data")
                        
                        os.makedirs(data_folder, exist_ok=True)
                        
                        data_dst = os.path.join(data_folder, os.path.basename(value))
                        if os.path.abspath(value) != os.path.abspath(data_dst):
                            if os.path.exists(data_dst):
                                os.remove(data_dst)
                            shutil.copy(value, data_dst)
                        
                        if data_type == 'eeg':
                            if value.lower().endswith('.set'):
                                fdt_file = os.path.splitext(value)[0] + '.fdt'
                                if os.path.exists(fdt_file):
                                    fdt_dst = os.path.join(data_folder, os.path.basename(fdt_file))
                                    if os.path.abspath(fdt_file) != os.path.abspath(fdt_dst):
                                        if os.path.exists(fdt_dst):
                                            os.remove(fdt_dst)
                                        shutil.copy(fdt_file, fdt_dst)
                            
                            elif value.lower().endswith('.vhdr'):
                                base_name = os.path.splitext(value)[0]
                                for ext in ['.vmrk', '.eeg']:
                                    associated_file = base_name + ext
                                    if os.path.exists(associated_file):
                                        associated_dst = os.path.join(data_folder, os.path.basename(associated_file))
                                        if os.path.abspath(associated_file) != os.path.abspath(associated_dst):
                                            if os.path.exists(associated_dst):
                                                os.remove(associated_dst)
                                            shutil.copy(associated_file, associated_dst)
                        
                        elif data_type == 'et' and value.endswith(('.gz', '.csv', '.asc', '.edf')):
                            et_src_dir = os.path.dirname(value)
                            for item in os.listdir(et_src_dir):
                                if item.endswith('.mp4') or item == 'meta':
                                    src_item = os.path.join(et_src_dir, item)
                                    dst_item = os.path.join(data_folder, item)
                                    if os.path.abspath(src_item) != os.path.abspath(dst_item):
                                        if os.path.isdir(src_item):
                                            if os.path.exists(dst_item):
                                                shutil.rmtree(dst_item)
                                            shutil.copytree(src_item, dst_item)
                                        else:
                                            if os.path.exists(dst_item):
                                                os.remove(dst_item)
                                            shutil.copy(src_item, dst_item)
                        
                        rel_path = os.path.relpath(data_dst, self.base_path)
                        updates.append(f"{key} = ?")
                        values.append(rel_path)
                else:
                    updates.append(f"{key} = ?")
                    values.append(value)

            if updates:
                query = f"UPDATE subjects SET {', '.join(updates)} WHERE id = ?"
                values.append(subject_id)
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
            return False

        except Exception as e:
            print(f"Error in Updating Participant Data: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_subject_data(self, subject_id: int, data_type: str, field: str, value: str) -> bool:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(f"UPDATE subjects SET {data_type}_{field}_path = ? WHERE id = ?", (value, subject_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Database Updating Error: {e}")
            return False
        finally:
            conn.close()

    def get_subject_data(self, subject_id: int) -> Dict[str, Any]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
            columns = [column[0] for column in cursor.description]
            values = cursor.fetchone()
            return dict(zip(columns, values)) if values else None
        finally:
            conn.close()

    def delete_subject(self, subject_id: int) -> bool:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error in Deleting Participant Record: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_project_info(self) -> Dict[str, Any]:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        info = {
            "project_name": self.project_name,
            "project_path": self.project_path,
            "experiments_count": 0,
            "subjects_count": 0
        }

        cursor.execute("SELECT COUNT(*) FROM experiments")
        info["experiments_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM subjects")
        info["subjects_count"] = cursor.fetchone()[0]

        conn.close()
        return info

    def delete_experiment(self, experiment_id: int) -> bool:
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            conn.execute("BEGIN")

            cursor.execute("SELECT name FROM experiments WHERE id = ?", (experiment_id,))
            experiment_name = cursor.fetchone()
            if not experiment_name:
                print(f"Experiment ID {experiment_id} Dosen't Exist")
                return False
            experiment_name = experiment_name[0]

            # experiment_path = os.path.join(self.project_path, experiment_name)
            # if os.path.exists(experiment_path):
            #     shutil.rmtree(experiment_path)

            cursor.execute("DELETE FROM subjects WHERE experiment_id = ?", (experiment_id,))

            cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))

            conn.commit()
            print(f"Experiment '{experiment_name}' Deleted")
            return True

        except Exception as e:
            conn.rollback()
            print(f"Error in Deleting Experiment: {str(e)}")
            return False

        finally:
            conn.close()

if __name__ == "__main__":
    project = Project("TestProject", ".")
    
    exp_id = project.add_experiment("Recogonitive Experiment")
    
    subject_id = project.add_subject(
        exp_id, 
        "zcy", 
        "Male", 
        25,
        fnirs_data_path="./gallery/app/view/data/P005T001.snirf",
        eeg_data_path="./gallery/app/view/data/eeglab_data.set",
        eeg_montage_path="./gallery/app/view/data/eeglab_chan32.locs",
        et_data_path="./gallery/app/view/data/gazedata.gz"
    )

    subjects = project.get_subjects(exp_id)
    print("Subjects in the experiment:")
    for subject in subjects:
        print(f"Name: {subject['name']}, Age: {subject['age']}, Gender: {subject['gender']}")

    project_info = project.get_project_info()
    print("\nProject Information:")
    for key, value in project_info.items():
        print(f"{key}: {value}")

    print("\nProject management operations completed successfully.")