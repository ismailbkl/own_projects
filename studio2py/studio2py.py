"""Usage:
  studiotopy.py -i (INPUT) -o (OUTPUT)
  studiotopy.py -h | --help

Options:
  -h --help     Show this screen.
"""

# !/usr/bin/python

from default_config import OrmTemplate, PYTHON_HEADER, PYTHON_HEADER_CLASS, PYTHON_HEADER_MANIFEST, PYTHON_FOOTER, \
    XML_HEADER, XML_FOOTER
from lxml import etree
import ast
import errno
import logging
import os
import sys
import shutil
import fileinput
import xml.etree.ElementTree as ET
import csv
from os import path

try:
    import autopep8
    from docopt import docopt
except ImportError:
    sys.exit(2)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def xmltodict(self):
    elt_dict = {}
    for elt in self:
        elt_dict[elt.attrib.get('name', False)] = elt.text
    return elt_dict


def get_manifest_info():
    info = {}
    manifest_file = input_path + '/__manifest__.py'
    if os.path.isfile(manifest_file):
        f = open(manifest_file, 'r')
        try:
            info.update(ast.literal_eval(f.read()))
        finally:
            f.close()
    return info


# TODO Find a better way to create a directory structure (skeleton ?)
def create_module_directory_structure(output_module):
    mkdir_p(os.path.join(os.getcwd(), output_module))
    mkdir_p(os.path.join(os.getcwd(), output_module, 'data'))
    mkdir_p(os.path.join(os.getcwd(), output_module, 'models'))
    mkdir_p(os.path.join(os.getcwd(), output_module, 'views'))
    mkdir_p(os.path.join(os.getcwd(), output_module, 'security/'))
    mkdir_p(os.path.join(os.getcwd(), output_module, 'static/description'))
    shutil.copy("icon.png", output_module + "/static/description/icon.png")


def generate_manifest(output_module, info):
    manifest_file = open(os.path.join(os.getcwd(), output_module, '__manifest__.py'), 'w')
    manifest_file.write(PYTHON_HEADER_MANIFEST)
    info.update({
        'name': 'Generated by studio2py ',
        'application': False,
        'author': 'Smile S.A',
        'auto_install': False,
        'category': 'Uncategorized',
        'description': '',
        'installable': True,
        'license': 'AGPL-3',
        'post_load': None,
        'version': '1.0',
        'web': False,
        'website': 'https://www.smile.eu',
        'sequence': 100,
        'summary': '',
    })
    manifest_file.write(str(info))
    manifest_file.close()


def fix_pep8(models_path):
    pep8_fixed = autopep8.fix_file(models_path + '.py')
    python_file = open(models_path + '.py', 'w')
    python_file.write(pep8_fixed)


def fix_xml_id_context(output_module):
    views_dir = output_module + '/views/'
    for f in os.listdir(views_dir):
        with fileinput.FileInput(views_dir + f, inplace=True) as file:
            for line in file:
                print(line.replace('id="studio_customization.', 'id="').replace("'studio': True", '')
                      .replace('ref="studio_customization.', 'ref="'))


def genarate_security_file(input_path, output_module):
    tree = ET.parse(input_path + 'data/ir_model_access.xml')
    root = tree.getroot()
    datas = [['id', 'name', 'model_id/id', 'group_id/id', 'perm_read', 'perm_create', 'perm_write', 'perm_unlink']]
    for record in root:
        # print record.tag, record.attrib
        data = [record.get('id').split('.')[1], '', '', '', '', '', '', '']
        for field in record:
            if field.attrib.get('name') == 'name':
                data[1] = field.text
            if field.attrib.get('name') == 'model_id':
                data[2] = "model_x_%s" % field.attrib.get('ref').split('.')[1].split('_')[0]
            if field.attrib.get('name') == 'group_id':
                data[3] = field.attrib.get('ref')
            if field.attrib.get('name') == 'perm_read':
                data[4] = '1' if field.attrib.get('eval') == 'True' else '0'
            if field.attrib.get('name') == 'perm_create':
                data[5] = '1' if field.attrib.get('eval') == 'True' else '0'
            if field.attrib.get('name') == 'perm_write':
                data[6] = '1' if field.attrib.get('eval') == 'True' else '0'
            if field.attrib.get('name') == 'perm_unlink':
                data[7] = '1' if field.attrib.get('eval') == 'True' else '0'
        datas.append(data)
    security_file = open(output_module + '/security/ir.model.access.csv', 'w')
    with security_file:
        writer = csv.writer(security_file)
        writer.writerows(datas)


def main(input_path, output_module):
    odoo_version = "10"
    odoo_server_path = ""

    info = get_manifest_info()
    dir_input = path.isdir(input_path)
    # verify if the path is a directory
    if not dir_input:
        logging.warning('You should extract the zip file before start the script execution!')
        sys.exit()
    # verify if the path ends by /
    if input_path[-1] != "/":
        logging.warning('Make sure that you input_path ends by "/"!')
        sys.exit()
    # retrieve the array of the xml files to be process
    if not info.get('data', False):
        logging.warning('Clause data in the studio manifest file is Empty !')
    else:
        data_files = info['data']
        create_module_directory_structure(output_module)
        # parse path of studio module and retrieve the xml file generated
        # the xml files are generated on the data directory
        # create a dict with for each model (models, fields, views, menus and actions)
        models = []
        models_tab = []
        fields = []
        views = {}
        for xml_file in data_files:
            # open the xml file
            f = open(os.path.join(os.getcwd(), input_path, xml_file), 'r')
            tree = etree.parse(f)
            # read records in files
            for records in tree.xpath("/odoo/record"):
                xml_values_dict = xmltodict(records)
                str_def = str(etree.tostring(records, pretty_print=True).decode())

                if 'ir_model_fields' in xml_file:
                    fields.append(xml_values_dict)
                elif 'ir_model.xml' in xml_file:
                    models.append(xml_values_dict)
                    models_tab.append(xml_values_dict['model'])
                elif 'ir_ui_view' in xml_file:
                    if not views.get(xml_values_dict['model'], False):
                        views[xml_values_dict['model']] = []
                    views[xml_values_dict['model']].append(str_def)
                elif 'ir_actions_act_window' in xml_file:
                    shutil.copy(input_path + xml_file, output_module + "/views/actions.xml")
                elif 'ir_ui_menu' in xml_file:
                    shutil.copy(input_path + xml_file, output_module + "/views/menus.xml")
                elif 'ir_model_access' in xml_file:
                    genarate_security_file(input_path, output_module)

        # Create python files for each new object
        # Create one dict for creating python files
        # Each new objet begin by x_ int the model name
        # Inherited model are fields began by x_ with model with not x_

        # Init dict for each object

        # Models and fields

        classes_dict = {}

        ormtemp = OrmTemplate()

        for field in fields:
            model_python_file = field['model'].replace('.', '_')
            if not classes_dict.get(model_python_file, False):
                classes_dict[model_python_file] = {}
                classes_dict[model_python_file]['python_header'] = ormtemp \
                    .generate_python_class_declaration(field['model'])
                classes_dict[model_python_file]['python_fields'] = []
                classes_dict[model_python_file]['python_computes'] = []

            classes_dict[model_python_file]['python_fields'].append(
                '\n    %s' % getattr(ormtemp, field['ttype'])(field))
            if field.get('compute', False):
                classes_dict[model_python_file]['python_computes'].append(ormtemp.generate_compute_function(field))

        # Generate python file by class
        init_file = []
        for name, classes in classes_dict.items():
            models_path = os.path.join(os.getcwd(), output_module, 'models', name)
            python_file = open(models_path + '.py', 'w')
            init_file.append(name + '.py')
            python_file.write(PYTHON_HEADER_CLASS)
            python_file.write(classes.get('python_header'))

            for fields in classes.get('python_computes', []):
                python_file.write(fields)

            for fields in classes.get('python_fields', []):
                python_file.write(fields)
            python_file.write(PYTHON_FOOTER)
            python_file.close()

            fix_pep8(models_path)

            # Generate __init__.py files for the module
            # Import each models
            models_path = os.path.join(os.getcwd(), output_module, 'models', '__init__')
            python_file = open(models_path + '.py', 'w')
            python_file.write(PYTHON_HEADER)

            for import_models in init_file:
                python_file.write('from . import %s \n' % import_models.replace('.py', ''))
            python_file.close()

            # Import model directory
            models_path = os.path.join(os.getcwd(), output_module, '__init__')
            python_file = open(models_path + '.py', 'w')
            python_file.write(PYTHON_HEADER)
            python_file.write('from . import models')
            python_file.close()

            # Create views, menu entry and action files
            # Update data in manifest file
            info["data"] = []
            # import pdb;
            # pdb.set_trace()

            for model, views_content in views.items():
                f = open(os.path.join(os.getcwd(), output_module, 'views/%s_views.xml') % model.replace('.', '_'), 'w')
                f.write(XML_HEADER)
                for view in views_content:
                    f.write(view)
                f.write(XML_FOOTER)
                f.close()
                info['data'].append('views/%s_views.xml' % model.replace('.', '_'))

        info['data'].extend(['security/ir.model.access.csv',
                             'views/actions.xml',
                             'views/menus.xml'])

        generate_manifest(output_module, info)
        os.system("autopep8 --in-place --aggressive --aggressive " + output_module + "/__manifest__.py")
        fix_xml_id_context(output_module)


if __name__ == "__main__":
    arguments = docopt(__doc__)
    input_path = arguments['INPUT']
    output_module = arguments['OUTPUT']
    main(input_path, output_module)