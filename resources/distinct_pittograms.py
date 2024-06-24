from flask_restful import Resource, reqparse, request
from datetime import datetime, timedelta
from models.comunicative_session.patient_cs_log import PatientCsLogModel
from models.user import UserModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
import calendar

from flask_jwt_extended import jwt_required

def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


class DistinctPictograms(Resource):

    @jwt_required()
    def get(self):

        date_start = request.args.get("date_start", type=parse_date, default=None)
        date_end = request.args.get("date_end", type=parse_date, default=None)
        patient_id = request.args.get("patient_id", type=int, default=None)
        centre_id = request.args.get("centre_id", type=int, default=None)
        operator_id = request.args.get("operator_id", type=int, default=None)
        week_view = request.args.get("week_view", type=lambda x: x.lower()=='true', default=True)

        if operator_id:
            if not patient_id:
                return {
                           "message": "Devi specificare il patient_id"
                       }, 400
        else:
            if not (patient_id or centre_id):
                return {
                           "message": "Devi specificare almeno patient_id oppure centre_id"
                       }, 400
            elif patient_id and centre_id:
                return {
                           "message": "Devi specificare patient_id oppure centre_id, non puoi inserirli entrambi"
                       }, 400

        return self.time_intervals_stat(date_start, date_end, patient_id, centre_id, operator_id, week_view)



    def time_intervals_stat(self, date_start, date_end, patient_id=None, centre_id=None, operator_id=None, week_view=True):
        pictograms = []
        used_pictograms = self.search_used_pictograms(date_start, patient_id, centre_id)
        while date_start < date_end:
            if not week_view:
                res = calendar.monthrange(date_start.year, date_start.month)
                last_day = res[1]
                data_fine_mese = date_start.replace(day=last_day)
                data_fine_mese = data_fine_mese.replace(hour=23, minute=59, second=59)
                if data_fine_mese > date_end:
                    data_fine_mese = date_end





            else:
                start = date_start - timedelta(days=date_start.weekday())
                data_fine_mese = start + timedelta(days=6)
                data_fine_mese = data_fine_mese.replace(hour=23, minute=59, second=59)
                if data_fine_mese > date_end:
                    data_fine_mese = date_end

            not_new_pictograms, new_pictograms = self.generate_query(date_start, data_fine_mese, used_pictograms, patient_id, centre_id, operator_id)

            used_pictograms = used_pictograms + new_pictograms
            pictograms.append({
                "date_start_interval": date_start.strftime("%d/%m/%Y"),
                "date_end_interval": data_fine_mese.strftime("%d/%m/%Y"),
                "n_pictograms_already_used": len(not_new_pictograms),
                "n_pictograms_new": len(new_pictograms)
            })
            date_start = data_fine_mese.replace(hour=0, minute=0, second=0) + timedelta(
                days=1)  # la data di inizio è la data di inizio di ogni intervallo
            # nella finestra temporale
        return pictograms

    def search_used_pictograms(self, date_start, patient_id=None, centre_id=None, operator_id=None):
        if operator_id:
            pcl_model_list = CsOutputImageModel.query.join(ComunicativeSessionModel).filter(
                ComunicativeSessionModel.patient_id == patient_id,
                ComunicativeSessionModel.user_id == operator_id,
                ComunicativeSessionModel.date < date_start.strftime("%Y-%m-%d")
            ).all()
        elif patient_id:
            pcl_model_list = PatientCsLogModel.query.filter(
                PatientCsLogModel.patient_id == patient_id,
                PatientCsLogModel.date < (date_start.strftime("%Y-%m-%d")
            )).all()
        elif centre_id:
            pcl_model_list = PatientCsLogModel.query.join(UserModel).filter(
                UserModel.autism_centre_id == centre_id,
                PatientCsLogModel.date < (date_start.strftime("%Y-%m-%d")
            )).all()

        used_pictograms = []
        for pict in pcl_model_list:
            if not any(pict.image_id == used_pict for used_pict in used_pictograms):
                used_pictograms.append(pict.image_id)
        return used_pictograms

    def generate_query(self, date_start, date_end, used_pictograms, patient_id=None, centre_id=None, operator_id=None):
        if operator_id:
            pcl_model_list = CsOutputImageModel.query.join(ComunicativeSessionModel).filter(
                ComunicativeSessionModel.patient_id == patient_id,
                ComunicativeSessionModel.user_id == operator_id,
                ComunicativeSessionModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d"))
            ).all()
        elif patient_id:
            pcl_model_list = PatientCsLogModel.query.filter(
                PatientCsLogModel.patient_id == patient_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d"))
            ).all()
        elif centre_id:
            pcl_model_list = PatientCsLogModel.query.join(UserModel).filter(
                UserModel.autism_centre_id == centre_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d"))
            ).all()

            pcl_model_list = list(filter(lambda x: x.image_id is not None, pcl_model_list ))

        not_new_pictograms = []
        new_pictograms = []

        for pcl in pcl_model_list:
            if not any(pcl.image_id == pict for pict in not_new_pictograms) and not any(pcl.image_id == pict for pict in new_pictograms):

                if pcl.image_id in used_pictograms:
                        not_new_pictograms.append(pcl.image_id)
                else:
                        new_pictograms.append(pcl.image_id)

        return not_new_pictograms, new_pictograms





