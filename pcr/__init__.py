from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename # not currently used
import os, subprocess, re, hashlib, pathlib

ORIG_UI = int(os.environ.get('ORIG_UI', 0)) > 0  # DEFAULT: False

app = Flask(__name__)
app.config['UPLOAD_PATH'] = 'seq'

# // https://github.com/kakulukia/pypugjs/blob/master/examples/flask/run.py
app.jinja_env.add_extension('pypugjs.ext.jinja.PyPugJSExtension')  # pyPUGjs

class Pipeline:
    # update the paths below to point to the correct location
    primer3_core_path = '/home/ubuntu/primer3/primer3_core'
    primersearch_path = '/usr/local/bin/primersearch'
    fasta_genome_path = '/home/ubuntu/PCR/genome/Homo_sapiens.GRCh38.dna.primary_assembly.fa'
    
    def __init__(self):
        self.seq = ''
        self.checksum = ''
        self.primer3_template_path = ''
        self.primer3_cli = ''
        self.primer3_output_path = ''
        self.primersearch_template_path = ''
        self.primersearch_cli = ''
        self.primersearch_output_path =''

    def sanitise_sequence(self, sequence):
        return re.sub('[^A|C|G|N|T]', '', sequence)
    
    def generate_checksum(self, sequence):
        return hashlib.md5(sequence.encode('utf-8')).hexdigest()
    
    def mkdirs(self, path):
        print("mkdirs")
        try:
            pathlib.Path(path).mkdir(parents=True, exist_ok=True)
            os.mkdir(path)  # [png1] This line was NOT pushed. (Perhaps NOT needed??)
        except OSError as error:
            print(error)
        self.primer3_template_path = pathlib.Path(path, 'primer3-template.txt')
        self.primer3_output_path = pathlib.Path(path, 'primer3-output.txt')
        self.primersearch_template_path = pathlib.Path(path, 'primersearch-template.txt')
        self.primersearch_output_path = pathlib.Path(path, 'primersearch-output.txt')

pcr = Pipeline()


APP_TITLE = 'PCR Workshop [Prototype], October 2021'

@app.route('/')
def upload_sequence():
    if ORIG_UI:
        return render_template('home.html')
    return render_template('base.pug',
        active_button='RUN_SETUP',
        app=dict(title=APP_TITLE, sub_title='Sequence'),
        # urls=dict(styles_css=url_for('static', filename='styles.css')),
    )

@app.route('/setup', methods=['POST'])
def setup():
    # get sequence data from the submitted form
    sequence = request.form['sequence'].upper()
    
    # remove all characters not A|C|G|N|T
    pcr.seq = pcr.sanitise_sequence(sequence)
    
    # generate checksum of sequence used to identify previous runs
    pcr.checksum = pcr.generate_checksum(pcr.seq)
    
    # setup folders are created to store output files
    pcr.mkdirs(pathlib.Path(app.instance_path, app.config['UPLOAD_PATH'], pcr.checksum))

    if ORIG_UI:
        return render_template('setup-sequence.html', pipeline=pcr)
    return render_template('base.pug',
        active_button='CREATE_PRIMER3_TEMPLATE',
        app=dict(title=APP_TITLE, sub_title='Sequence Setup'),
        pipeline=pcr
    )
    
@app.route('/primer3-template', methods=['POST'])
def primer3_template():
    
    # check if template file exists
    template=''
    if os.path.exists(pcr.primer3_template_path):
        # existing template file found, open
        try:
            with open(pcr.primer3_template_path, 'r') as f:
                template = f.read()
        except IOError as error:
            print(error)
    else:
        # no previous template file found, create
        try:
            with open(pcr.primer3_template_path, 'w') as f:
                template = render_template('primer3-template.txt', pipeline=pcr)
                f = open(pcr.primer3_template_path, "w")
                f.writelines(template)
        except IOError as error:
                print(error)

    # generate primer3 cli command
    pcr.primer3_cli = render_template('primer3-cli.txt', pipeline=pcr)

    if ORIG_UI:
        return render_template('primer3-template.html', template=template, pipeline=pcr)
    return render_template('base.pug',
        active_button='RUN_PRIMER3',
        app=dict(title=APP_TITLE, sub_title='Primer3 Template'),
        pipeline=pcr,
        template=template
    )

@app.route('/primer3-run', methods=['POST'])
def primer3_run():
    # check previous results
    result=''
    if os.path.exists(pcr.primer3_output_path):
        # existing results file found, open
        try:
            with open(pcr.primer3_output_path, 'r') as f:
                result = f.read()
        except IOError as error:
                print(error)
    else:
        # no previous results file found, run primer3
        command = request.form['cli']
        result_cli = subprocess.check_output([command], shell=True, universal_newlines=True)
        try:
            with open(pcr.primer3_output_path, 'r') as f:
                result = f.read()
        except IOError as error:
                print(error)       
    
    # get value from primer3 output
    primer3_output_pairs = dict(s.split('=', 1) for s in result[:-1].split('\n'))
    
    # check if template exists
    template=''
    if os.path.exists(pcr.primersearch_template_path):
        # existing template file found, open
        try:
            with open(pcr.primersearch_template_path, 'r') as f:
                template = f.read()
        except IOError as error:
            print(error)
    else:
        # no previous template file found, create
        try:
            with open(pcr.primersearch_template_path, 'w') as f:
                template = render_template('primersearch-template.txt', pairs=primer3_output_pairs)
                f = open(pcr.primersearch_template_path, "w")
                f.writelines(template)
        except IOError as error:
                print(error)
        
    # generate primersearch cli command
    pcr.primersearch_cli = render_template('primersearch-cli.txt', pipeline=pcr)

    if ORIG_UI:
        return render_template('primer3-output.html', result=result, template=template, pipeline=pcr)
    return render_template('base.pug',
        active_button='RUN_PRIMERSEARCH',
        app=dict(title=APP_TITLE, sub_title='Primer3 Output'),
        pipeline=pcr,
        template=template,
        result=result
    )

@app.route('/primersearch-run', methods=['POST'])
def primersearch_run():
    # check previous results
    result=''
    if os.path.exists(pcr.primersearch_output_path):
        # existing results file found, open
        try:
            with open(pcr.primersearch_output_path, 'r') as f:
                result = f.read()
        except IOError as error:
                print(error)
    else:
        # no previous results file found, run primer3
        command = request.form['cli']
        result_cli = subprocess.check_output([command], shell=True, universal_newlines=True)
        try:
            with open(pcr.primersearch_output_path, 'r') as f:
                result = f.read()
        except IOError as error:
                print(error)       

    if ORIG_UI:
        return render_template('primersearch-output.html', pipeline=pcr, result=result)
    return render_template('base.pug',
        active_button='',
        app=dict(title=APP_TITLE, sub_title='Primersearch Output'),
        pipeline=pcr,
        result=result
    )
