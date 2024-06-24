from flask_restful import Resource, reqparse, request
from datetime import datetime, timedelta
from models.comunicative_session.patient_cs_log import PatientCsLogModel
from models.user import UserModel
from models.grammatical_type import GrammaticalTypeModel
from models.image import ImageModel
from models.comunicative_session.comunicative_session import ComunicativeSessionModel
from models.comunicative_session.cs_output_image import CsOutputImageModel
import calendar

from flask_jwt_extended import jwt_required

def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


class GrammaticalTypesUsage(Resource):

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
        evoluzione_gramm = []


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

            gramm_types_distinct_count = self.generate_query(date_start, data_fine_mese, patient_id, centre_id, operator_id)


            evoluzione_gramm.append({
                    "date_start_interval": date_start.strftime("%d/%m/%Y"),
                    "date_end_interval": data_fine_mese.strftime("%d/%m/%Y"),
                    "values" : gramm_types_distinct_count
            })
            date_start = data_fine_mese.replace(hour=0, minute=0, second=0) + timedelta(
                days=1)  # la data di inizio è la data di inizio di ogni intervallo
            # nella finestra temporale

        return evoluzione_gramm





    def generate_query(self, date_start, date_end, patient_id=None, centre_id=None, operator_id=None):
        if operator_id:
            pcl_model_list = CsOutputImageModel.query.join(ComunicativeSessionModel).filter(
                ComunicativeSessionModel.patient_id == patient_id,
                ComunicativeSessionModel.user_id == operator_id,
                ComunicativeSessionModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d"))
            ).all()
        elif patient_id:
            pcl_model_list = PatientCsLogModel.query.filter(

                PatientCsLogModel.patient_id == patient_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")),
                PatientCsLogModel.log_type == "INSERT_IMAGE"
            ).all()
        elif centre_id:
            pcl_model_list = PatientCsLogModel.query.join(UserModel).filter(

                UserModel.autism_centre_id == centre_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"), date_end.strftime("%Y-%m-%d")),
                PatientCsLogModel.log_type == "INSERT_IMAGE"
            ).all()

        pcl_model_list = list(filter(lambda x: x.image_id is not None, pcl_model_list ))
        image_list = [cs_log.image for cs_log in pcl_model_list]
        gramm_types_distinct_count = []


        for image in image_list:
            for gt in image.image_grammatical_type:
                if not any(gt.type == gramm_count["gramm_type"] for gramm_count in gramm_types_distinct_count):
                    gramm_types_distinct_count.append({
                        "gramm_type": gt.type,
                        "count_distinct": 1,
                        "image_list" : [
                            {"image_id" : image.id,
                             "label" : image.label,
                             "count" : 1}
                        ]
                    })
                else:
                    gramm_count = list(filter(lambda x: x["gramm_type"] == gt.type, gramm_types_distinct_count))[0]

                    if not any(image.id == image_count["image_id"] for image_count in gramm_count["image_list"]):
                        gramm_count["image_list"].append({
                            "image_id": image.id,
                            "label": image.label,
                            "count": 1
                        })
                        gramm_count["count_distinct"] = gramm_count["count_distinct"] +1
                    else:
                        image_count = list(filter(lambda x: x["image_id"] == image.id, gramm_count["image_list"]))[0]
                        image_count["count"] = image_count["count"] + 1

                   # image_distinct_list.append(
                     #   {"image_id" : image.id,
                     #    "type" : gt.type})
                   # if any(gt.type == gramm_count["gramm_type"] for gramm_count in gramm_types_distinct_count):
                       # gramm_count = list(
                           # filter(lambda x: x["gramm_type"] == gt.type, gramm_types_distinct_count))[0]
                    #gramm_count["count_distinct"] = gramm_count["count_distinct"] + 1


        return gramm_types_distinct_count





