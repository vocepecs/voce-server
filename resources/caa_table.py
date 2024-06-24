from multiprocessing import context
from models.image import ImageModel
from models.tag import TagModel
from models.caa_table import CaaTableModel
from models.patient import PatientModel, PatientCaaTableModel
from models.table_sector import TableSectorImage, TableSectorModel
from models.user import UserModel
from flask_restful import Resource, reqparse, request
from datetime import datetime
from models.context import ContextModel
import math


from flask_jwt_extended import jwt_required


def parse_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")

class CaaTable(Resource):

    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', type=str)
        self.parser.add_argument('table_format', type=str)
        self.parser.add_argument('creation_date', type=parse_date)
        self.parser.add_argument('last_modify_date', type=parse_date)
        self.parser.add_argument('is_active', type=bool)
        self.parser.add_argument('description', type=str)
        self.parser.add_argument('image_string_coding', type=str)
        self.parser.add_argument('is_private', type=bool)
        self.parser.add_argument('autism_centre_id', type=int)
        self.parser.add_argument('sector_list', type=dict, action='append')

    @jwt_required()
    def post(self):

        # Get input data e parameters
        args = self.parser.parse_args()
        patient_id = request.args.get('patient_id', type=int, default=None)
        user_id = request.args.get('user_id', type=int, default=None)
        original_table_id = request.args.get('original_table_id', type=int, default=None)

        caa_table = CaaTableModel(
            args['name'],
            args['table_format'],
            args['creation_date'],
            args['last_modify_date'],
            args['is_active'],
            args['description'],
            args['image_string_coding'],
            user_id,
            args['autism_centre_id'],
            args['is_private']
        )

        caa_table_id = caa_table.save_to_db()

        # Creazione dei settori per il salvataggio delle immagini in tabella
        json_sector_list = args['sector_list']
        for json_sector in json_sector_list:
            table_sector = TableSectorModel(
                int(json_sector['id']),
                caa_table_id,
                json_sector['sector_color'],
                json_sector['table_sector_number'],
            )
            for image in json_sector['image_list']:
                image_model = ImageModel.find_by_id(image['id'])
                table_sector.images.append(image_model)
            table_sector.save_to_db()

        # Associazione Tabella - Paziente
        if patient_id:
            pt_association = PatientCaaTableModel(patient_id,caa_table_id,original_table_id)
            pt_association.save_to_db()


        return {"message": "Caa Table created successfully.",
                "caa_table_id": caa_table_id, }, 201

    @jwt_required()
    def put(self):
        caa_table_id = request.args.get('caa_table_id', type=int, default=None)
        caa_table = CaaTableModel.find_by_id(caa_table_id)
        args = self.parser.parse_args()

        for attr in args.keys():
            if attr in args:
                setattr(caa_table, attr, args[attr])

        caa_table.last_modify_date = datetime.now()

        


        # TODO aggiornare la parte client
        caa_table.title = args['name']
        
        caa_table.save_to_db()

        ### TODO Ottimizzare inserendo delle condizioni sull'aggiornamento dei settori
        ### TODO Se non vi è alcuna modifica del/dei settori, non vengono aggiornati

        # Clear table sectors
        for table_sector in caa_table.table_sectors:
            table_sector.delete_from_db()

        # Insert Updated sectors
        json_sector_list = args['sector_list']
        for json_sector in json_sector_list:
            table_sector = TableSectorModel(
                int(json_sector['id']),
                caa_table_id,
                json_sector['sector_color'],
                json_sector['table_sector_number'],
            )
            for image in json_sector['image_list']:
                image_model = ImageModel.find_by_id(image['id'])
                table_sector.images.append(image_model)
            table_sector.save_to_db()

        return {"message": "Caa Table updated successfully."}, 200

    '''
    Vecchio algortimo per l'assegnazione dei contesti alla tabella
    '''
    def setCaaTableContexts(self, id_table):
        image_list = []
        # Lavoro sulla tabella
        caa_table = CaaTableModel.find_by_id(id_table)
        sector_list = caa_table.table_sectors
        for sector in sector_list:
            # print(sector)
            for image in sector.images:
                image_list.append(image.json())

        dict_contesti = {}

        for image in image_list:

            general_tag_list = list(filter(lambda x: (x.get == 'GENERAL' and ((x.get != 'comunicazione') and ('verbo' not in x.get) and (x.get != 'linguaggio') and (x.get != 'vocabolario di base'))), image.get))
            for tag in general_tag_list:
                print(tag)
                print(tag.get)
                if tag.get not in dict_contesti.keys():
                    dict_contesti[tag.get] = 1
                    print(dict_contesti.keys())

                else:
                    print('OK')
                    dict_contesti[tag.get] = dict_contesti[tag.get] + 1

        tupl_contesti = sorted(dict_contesti.items(), key=lambda x: x[1])
        print(dict_contesti)

        soglia = math.ceil((30/100)*len(tupl_contesti))
        print(soglia)
        for i in reversed(tupl_contesti):
            # print('len',len(tupl_contesti))
            index_tup = len(tupl_contesti)-tupl_contesti.index(i)
            print('index', index_tup)
            # print(i[1])
            if index_tup <= soglia:
                print(i[0])
                tag = TagModel.find_by_id(i[0])
                print(tag.tag_value)
                context = ContextModel.find_by_value(tag.tag_value)
                if context:
                    print(context)
                    print(caa_table.id)
                    caa_table.add_context(context)
                else:
                    context = ContextModel(tag.tag_value)
                    context.save_to_db()
                    context = ContextModel.find_by_value(tag.tag_value)
                    caa_table.add_context(context)

            # print(caa_table.find_by_id(56))

    def get(self):
        caa_table_id = request.args.get('caa_table_id', type=int, default=None)
        caa_table = CaaTableModel.find_by_id(caa_table_id)
        if not caa_table:
            return {"message": "CAA Table not found"}, 404
        return caa_table.json(), 200

    def delete(self):
        caa_table_id = request.args.get('caa_table_id', type=int, default=None)
        caa_table = CaaTableModel.find_by_id(caa_table_id)
        if not caa_table:
            return {'message': 'CAA Table not found'}, 404
        caa_table.is_deleted = True
        caa_table.save_to_db()
        return {'message': 'Table deleted.'}, 200



# ! VA RIMOSSA! Sostituita con il metodo put 
class ActiveCaaTable(Resource):
    @jwt_required()
    def post(self):
        caa_table_id = request.args.get('caa_table_id', type=int, default=None)
        patient_id = request.args.get('patient_id', type=int, default=None)
        patient = PatientModel.find_by_id(patient_id)
        patient.set_active_table(caa_table_id)
        return {"message": "Active table update successfully."}, 200


class CaaTableListTest(Resource):
    
    @jwt_required()
    def get(self):
        pattern = request.args.get('pattern', None)
        user_id = request.args.get('user_id', type=int, default=None)

        search_by_owner = request.args.get(
            'search_by_owner',
            type=lambda v: v.lower() == 'true',
            default=False
        )
        
        autism_centre_id = request.args.get(
            'autism_centre_id',
            type=int,
            default=None
        )

        search_default = request.args.get(
            'search_default',
            type=lambda v: v.lower() == 'true',
            default=False
        )

        print(f'pattern: {pattern}')
        print(f'user: {user_id}')
        print(f'autism centre: {autism_centre_id}')

        caa_table_list = []

        if pattern != 'null':
            caa_table_list.extend(
                CaaTableModel.find_public_tables(pattern=pattern))
        if user_id:
            if search_by_owner == True:
                caa_table_list.extend(
                    CaaTableModel.find_owner_tables(user_id=user_id))
            else:
                caa_table_list.extend(
                    CaaTableModel.find_private_tables(user_id=user_id))
        
        if autism_centre_id:
            caa_table_list.extend(CaaTableModel.find_centre_tables(
                autism_centre_id=autism_centre_id))


        if search_default == True:
            caa_table_list.extend(CaaTableModel.find_default_tables())

        # Se user_id o autism_centre_id sono specificati cerca le tabelle private
        return {
            "caa_tables": [caa_table.json() for caa_table in caa_table_list]
        }, 200

class CaaTableList(Resource):
    def get(self):
        pattern = request.args.get('pattern', type=str, default=None)
        user_id = request.args.get('user_id', type=int, default=None)

        search_by_owner = request.args.get(
            'search_by_owner',
            type=lambda v: v.lower() == 'true',
            default=False
        )
        
        autism_centre_id = request.args.get(
            'autism_centre_id',
            type=int,
            default=None
        )

        search_default = request.args.get(
            'search_default',
            type=lambda v: v.lower() == 'true',
            default=False
        )

        search_most_used = request.args.get(
            'search_most_used',
            type=lambda v: v.lower() == 'true',
            default=False
        )

        print(f'pattern: {pattern}')
        print(f'user: {user_id}')
        print(f'autism centre: {autism_centre_id}')
        print(f'search default: {search_default}')
        print(f'search by owner: {search_by_owner} | type: {type(search_by_owner)}')

        caa_table_list = []

        if pattern:
            caa_table_list.extend(
                CaaTableModel.find_public_tables(pattern=pattern))
            
        if user_id:
            if search_by_owner == True:
                caa_table_list.extend(
                    CaaTableModel.find_owner_tables(user_id=user_id))
            elif search_most_used == True:
                caa_table_list.extend(CaaTableModel.find_most_used_tables(user_id=user_id))
            else:
                caa_table_list.extend(
                    CaaTableModel.find_private_tables(user_id=user_id))
        
        if autism_centre_id:
            caa_table_list.extend(CaaTableModel.find_centre_tables(
                autism_centre_id=autism_centre_id))


        if search_default == True:
            caa_table_list.extend(CaaTableModel.find_default_tables())        
        
        print(f"caa_table_list: ", caa_table_list)

        # Se user_id o autism_centre_id sono specificati cerca le tabelle private
        return {
            "caa_tables": [caa_table.json() for caa_table in caa_table_list]
        }



# ? Verificarne l'utilizzo
class AddImageToTable(Resource):
    def post(self):
        caa_table_id = request.args.get('caa_table_id', type=int, default=None)
        table_sector_id = request.args.get('table_sector_id', None)
        image_id = request.args.get('image_id', type=int, default=None)

        caa_table = CaaTableModel.find_by_id(caa_table_id)
        if not caa_table:
            return {"message": "Caa Table not found"}, 404
        image = ImageModel.find_by_id(image_id)
        if not image:
            return {"message": "Image not found"}, 404
        table_sector = TableSectorModel.find_by_id(
            table_sector_id, caa_table_id)
        if not table_sector:
            return {"message": "Table sector not found"}, 404

        table_sector.images.append(image)
        table_sector.save_to_db()
        return {"message": "Image added successfully."}, 201
