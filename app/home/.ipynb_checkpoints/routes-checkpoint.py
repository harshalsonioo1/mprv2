# -*- encoding: utf-8 -*-

import os
import mlflow
from app.home import blueprint
from flask import render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import login_manager
from jinja2 import TemplateNotFound
from pathlib import Path
import json
from collections import defaultdict


DEFAULT_CLIENT_NAME = 'Dominion-Utah'
CURRENT_VIEW = 'index'

EXPERIMENT_NAME = "MPR_v1.0_test"
CS_STANDARD = ['historical_damage_rates_ticketed_damages.png', 
               'percent_ticketed_damages_changed_year2020.png', 
               'adjusted_highest_catch_rate.png']
CS_ADVANCED = ['percentage_interventions_per_bucket.png',
              'damage_rate_odds_ratio.png',
              'damage_rate_odds_ratio_log.png',
              'data_volume.png']
MLBOARD = ['percent_ticketed_damages_changed_year2020.png',
          'damage_rate_odds_ratio_log.png',
          'damage_rate_odds_ratio.png',
          'data_volume.png']
OTHERS = CS_ADVANCED + CS_STANDARD + MLBOARD

VIEW_PATHS = {'index.html': CS_STANDARD,
                'index': CS_STANDARD,
                'csadvanced.html': CS_ADVANCED,
                'ml.html': MLBOARD,
                'others.html': OTHERS}

def download_fresh_artifacts():
    experiment_name = EXPERIMENT_NAME
    
    try:
        current_experiment=dict(mlflow.get_experiment_by_name(experiment_name))
        experiment_id=current_experiment['experiment_id']

        df = mlflow.search_runs([experiment_id])
        run_df = df.sort_values(['start_time', 'params.client_name'], ascending=(False, False)).drop_duplicates(subset='params.client_name', keep="first")

        for run_id, client_name in zip(run_df['run_id'], run_df['params.client_name']):
            target_dir = os.path.join('app/base/static/assets/clients', client_name)
            if not os.path.isdir(target_dir):
                Path(f'{target_dir}').mkdir(parents=True, exist_ok=True)
                os.system(f'gsutil cp gs://core-data-lake/experimental/mlflow/artifacts/{experiment_id}/{run_id}/artifacts/** {target_dir}')

        return run_df['params.client_name']
    except:
        pass


def get_artifacts(client_name, view_paths):

    target_dir = os.path.join('app/base/static/assets/clients', client_name)

    return list(set(os.listdir(target_dir)).intersection(set(view_paths)))


@blueprint.route('/index')
@login_required
def index():
    client_list = download_fresh_artifacts()
    client_paths_png = get_artifacts(client_name=DEFAULT_CLIENT_NAME, view_paths=CS_STANDARD)
    
    return render_template('index.html', segment='index', client_list=client_list, client_paths_png=client_paths_png, selected_client=DEFAULT_CLIENT_NAME)


@blueprint.route('/client/<client_name>')
@login_required
def client(client_name):
    
    global DEFAULT_CLIENT_NAME
    DEFAULT_CLIENT_NAME = client_name
    
    client_list = download_fresh_artifacts()
    client_paths_png = get_artifacts(client_name=client_name, view_paths=VIEW_PATHS[CURRENT_VIEW])
    return render_template(CURRENT_VIEW, segment=CURRENT_VIEW, client_list=client_list, client_paths_png=client_paths_png, selected_client=client_name)


@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:
        global CURRENT_VIEW
        CURRENT_VIEW = template
        
        if not template.endswith( '.html' ):
            template += '.html'

        # Detect the current page
        segment = get_segment( request )
        
        # Download Client List Active
        client_list = download_fresh_artifacts()
        
        # Serve the file (if exists) from app/templates/FILE.html
        
        if template.startswith('csadvanced'):
            
            client_paths_png = get_artifacts(client_name=DEFAULT_CLIENT_NAME, view_paths=CS_ADVANCED)

            return render_template( template, segment=segment, client_list=client_list, client_paths_png=client_paths_png, selected_client=DEFAULT_CLIENT_NAME)
        
        if template.startswith('ml'):
            
            client_paths_png = get_artifacts(client_name=DEFAULT_CLIENT_NAME, view_paths=MLBOARD)

            return render_template( template, segment=segment, client_list=client_list, client_paths_png=client_paths_png, selected_client=DEFAULT_CLIENT_NAME)

        if template.startswith('others'):
            
            client_paths_png = get_artifacts(client_name=DEFAULT_CLIENT_NAME, view_paths=OTHERS)

            return render_template( template, segment=segment, client_list=client_list, client_paths_png=client_paths_png, selected_client=DEFAULT_CLIENT_NAME)
        
        
    except TemplateNotFound:
        return render_template('page-404.html'), 404
    
    except:
        return render_template('page-500.html'), 500

# Helper - Extract current page name from request 
def get_segment( request ): 

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment    

    except:
        return None  
