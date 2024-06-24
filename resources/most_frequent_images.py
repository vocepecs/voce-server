from flask_restful import Resource, request
from datetime import datetime
from models import PatientCsLogModel, UserModel, CsOutputImageModel, ComunicativeSessionModel

from flask_jwt_extended import jwt_required


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")

class ImageFrequenceGraph(Resource):

    @jwt_required()
    def get(self):

        date_start = request.args.get("date_start", type=parse_date, default=None)
        date_end = request.args.get("date_end", type=parse_date, default=None)
        patient_id = request.args.get("patient_id", type=int, default=None)
        centre_id = request.args.get("centre_id", type=int, default=None)
        operator_id = request.args.get("operator_id", type=int, default=None)

        print(f"date start: {date_start}")
        print(f"date end: {date_end}")

        date_start_str = datetime.strftime(date_start,"%Y-%m-%d")
        date_end_str = datetime.strftime(date_end,"%Y-%m-%d")

        print(f"START: {date_start_str}\nEND: {date_end_str}")

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


        image_id_count = self.generate_query(
            date_start,
            date_end,
            patient_id,
            centre_id,
            operator_id
        
        )
        if len(image_id_count):
            ord_image_id_count = sorted(image_id_count, key=lambda x: x["count"], reverse=True)
            return ord_image_id_count, 200
        else:
            return {
                "message": "Nessuna immagine trovata"
            }, 404




    def generate_query(self, date_start, date_end, patient_id=None, centre_id=None, operator_id = None):

        image_list = [] # Lista di ImageModel
        image_id_count = [] # Output: Lista di dizionari con il count per ogni id e label
        if operator_id:
                cs_log_list = CsOutputImageModel.query.join(ComunicativeSessionModel).filter(
                ComunicativeSessionModel.patient_id == patient_id,
                ComunicativeSessionModel.user_id == operator_id,
                ComunicativeSessionModel.date.between(date_start.strftime("%Y-%m-%d"),date_end.strftime("%Y-%m-%d"))
            ).all()

        elif patient_id:

            cs_log_list = PatientCsLogModel.query.filter(
                PatientCsLogModel.patient_id == patient_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"),
                                               date_end.strftime("%Y-%m-%d")),
                PatientCsLogModel.log_type == "INSERT_IMAGE"
            ).all()

        elif centre_id:

            cs_log_list = PatientCsLogModel.query.join(UserModel).filter(
                UserModel.autism_centre_id == centre_id,
                PatientCsLogModel.date.between(date_start.strftime("%Y-%m-%d"),date_end.strftime("%Y-%m-%d")),
                PatientCsLogModel.log_type == "INSERT_IMAGE"
            ).all()

        print(cs_log_list)
        image_list = [cs_log.image for cs_log in cs_log_list]
        # image_list = list(filter( lambda x: x is not None, image_list))

        print(f"image_model_list: {len(image_list)}\n{image_list}")

        for image in image_list:

                if any(image.id == image_count["image_id"] for image_count in image_id_count):
                
                    image_count = list(
                        filter(lambda x: x["image_id"] == image.id, image_id_count))[0]
                    
                    image_count["count"] = image_count["count"] + 1

                else:
                    image_id_count.append({
                        "image_id": image.id,
                        "count": 1,
                        "label": image.label
                    })

        return image_id_count
