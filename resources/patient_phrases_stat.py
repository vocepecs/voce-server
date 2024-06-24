from flask_restful import Resource, reqparse, request
from datetime import datetime, timedelta
from models.comunicative_session.patient_cs_log import PatientCsLogModel
from models.user import UserModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
import calendar
from statistics import mean

from flask_jwt_extended import jwt_required


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")




class PhraseStatistics(Resource):

    @jwt_required()
    def get(self):
        phrase_stat = []
        date_start = request.args.get("date_start", type=parse_date, default=None)
        date_end = request.args.get("date_end", type=parse_date, default=None)
        patient_id = request.args.get("patient_id", type=int, default=None)
        centre_id = request.args.get("centre_id", type=int, default=None)
        operator_id = request.args.get("operator_id", type=int, default=None)
        week_view = request.args.get("week_view", type=lambda x: x.lower()=='true', default=True)

        date_start_str = datetime.strftime(date_start, "%Y-%m-%d")
        date_end_str = datetime.strftime(date_end, "%Y-%m-%d")

        if operator_id:
            if not patient_id:
                return {
                           "message": "Devi specificare patient_id"
                       }, 400
        else:
            if not patient_id and not centre_id:
                return {
                           "message": "Devi specificare almeno patient_id oppure centre_id"
                       }, 400
            elif patient_id and centre_id:
                return {
                           "message": "Devi specificare patient_id oppure centre_id, non puoi inserirli entrambi"
                       }, 400

        phrase_stat = self.time_intervals_stat(date_start, date_end, week_view, patient_id, centre_id, operator_id)
        return phrase_stat, 200

    def time_intervals_stat(self, date_start, date_end, week_view, patient_id=None, centre_id=None, operator_id=None):
        phrase_stat = []

        while date_start < date_end:
            if not week_view:
                res = calendar.monthrange(date_start.year, date_start.month)
                last_day = res[1]
                data_fine_periodo = date_start.replace(day=last_day)
                data_fine_periodo = data_fine_periodo.replace(hour=23, minute=59, second=59)
                if data_fine_periodo > date_end:
                    data_fine_periodo = date_end

            elif week_view:
                start = date_start - timedelta(days=date_start.weekday())
                data_fine_periodo = start + timedelta(days=6)
                data_fine_periodo= data_fine_periodo.replace(hour=23, minute=59, second=59)
                if data_fine_periodo > date_end:
                    data_fine_periodo = date_end



            phrase_length, time_pitt = self.generate_query(date_start, data_fine_periodo, patient_id, centre_id, operator_id)

            mean_length = round(mean(phrase_length), 2)
            max_length_phrase = max(phrase_length)
            min_length_phrase = min(phrase_length)


            if operator_id:
                phrase_stat.append({
                    "date_start_interval": date_start.strftime("%d/%m/%Y"),
                    "date_end_interval": data_fine_periodo.strftime("%d/%m/%Y"),
                    "mean_length": mean_length,
                    "max_length": max_length_phrase,
                    "min_length": min_length_phrase
                })
            else:
                mean_time = round(mean(time_pitt), 2)
                max_length_time = max(time_pitt)
                min_length_time = min(time_pitt)
                phrase_stat.append({
                    "date_start_interval": date_start.strftime("%d/%m/%Y"),
                    "date_end_interval": data_fine_periodo.strftime("%d/%m/%Y"),
                    "mean_length": mean_length,
                    "max_length": max_length_phrase,
                    "min_length": min_length_phrase,
                    "mean_time": mean_time,
                    "max_time": max_length_time,
                    "min_time": min_length_time
                })
            date_start = data_fine_periodo.replace(hour=0, minute=0, second=0) + timedelta(
                days=1)  # la data di inizio è la data di inizio di ogni intervallo
            # nella finestra temporale
        return phrase_stat

    def generate_query(self, date_start, date_end, patient_id=None, centre_id=None, operator_id=None):

        length_phrase = []
        time_pitt = []
        if operator_id:
            coi_model_list = CsOutputImageModel.query.join(ComunicativeSessionModel).filter(
                ComunicativeSessionModel.patient_id == patient_id,
                ComunicativeSessionModel.user_id == operator_id,
                ComunicativeSessionModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d"))
            ).all()

            last_cs_id = 0
            for coi in coi_model_list:
                if coi.comunicative_session_id != last_cs_id:
                    words_number_in_phrase = list(filter(lambda x: x.comunicative_session_id == coi.comunicative_session_id, coi_model_list))
                    length_phrase.append(len(words_number_in_phrase))
            if len(length_phrase) == 0:
                length_phrase.append(0)


        else:
            if patient_id:
                pcl_model_list = PatientCsLogModel.query.filter(
                    PatientCsLogModel.patient_id == patient_id,
                    PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")),
                    PatientCsLogModel.log_type == "INSERT_IMAGE"
                ).order_by(PatientCsLogModel.patient_id, PatientCsLogModel.date, PatientCsLogModel.id).all()
            elif centre_id:
                pcl_model_list = PatientCsLogModel.query.join(UserModel).filter(
                    UserModel.autism_centre_id == centre_id,
                    PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")),
                    PatientCsLogModel.log_type == "INSERT_IMAGE"
                ).order_by(PatientCsLogModel.patient_id, PatientCsLogModel.date, PatientCsLogModel.id).all()


            pos = 0
            last_time = 0
            id_frase = 0
            frase_corretta = 0
            for pcl in pcl_model_list:

                if isinstance(pcl.image_position, int):
                    current_pos = pcl.image_position
                    current_date = pcl.date

                    if current_pos == 0:
                        if frase_corretta == 1:
                            length_phrase.append(pos)
                            id_frase = id_frase + 1
                        frase_corretta = 1
                        pos = 1



                    elif current_pos != 0 and frase_corretta == 1:
                        if current_pos <= pos and (current_date - last_time) < timedelta(minutes=30):
                            pos = current_pos + 1
                            time_interval = current_date - last_time
                            time_pitt.append(time_interval.seconds)
                        elif current_pos <= pos and (current_date - last_time) > timedelta(minutes=30) or current_pos > pos:
                            frase_corretta = 0
                            length_phrase.append(pos)

                last_time = current_date

            if id_frase == 0 and pos == 0:

                length_phrase.append(0)

                time_pitt.append(0)


            elif frase_corretta == 1:

                length_phrase.append(pos)

        return length_phrase, time_pitt
