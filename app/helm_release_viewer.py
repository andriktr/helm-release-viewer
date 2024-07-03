#!/usr/bin/env python

# Standard library imports
import os
import time
import logging
import sys
import json
import concurrent
import subprocess
import requests
import datetime
import yaml

# Third-party imports
from prettytable import PrettyTable
from tabulate import tabulate
from kubernetes import client, config
from flask import Flask, render_template, request, redirect, url_for, session
from concurrent.futures import ThreadPoolExecutor
from cachetools import cached, TTLCache
from builtins import NameError
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler



# Logging configuration
logging.basicConfig(level=logging.INFO , stream=sys.stdout, format='%(asctime)s %(levelname)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S %p')

# Get the selectors from the environment variables
selectors_env = os.environ.get("SELECTORS", None)
environment = os.environ.get("ENVIRONMENT", "")
cache_ttl = int(os.environ.get("CACHE_TTL", 300))
cache_size = int(os.environ.get("CACHE_SIZE", 50000))
app_port = int(os.environ.get("APP_PORT", 8080))
app_warmup_interval = int(os.environ.get("APP_WARMUP_INTERVAL", 300))
log_level = os.environ.get("LOG_LEVEL", "info")
in_cluster = os.environ.get("IN_CLUSTER", "true")

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)

# Create a cache object with a TTL of 5 minutes and a max size of 50000 (default values)
cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

# Load kubeconfig from default location
try:
    logging.info("Loading kubeconfig")
    if in_cluster.lower() == "true": 
        config.load_incluster_config()
    else:
        config.load_kube_config()
except Exception as e:
    logging.error(f"Error loading kubeconfig: {e}")
    raise Exception("Error loading kubeconfig") from e

def clear_cache():
    cache.clear()
    return "Cache has been cleared"

# Parse the selectors_env string into a list of selectors
if selectors_env is None or selectors_env == "":
    logging.info(f"No selectors provided. All namespaces will be listed.")
    selectors_list = []
else:
    selectors_list = selectors_env.split(',')

# Function to get the namespaces based on the label selectors empty list will return all namespaces
@cached(cache)
def get_namespace_names_based_on_either_label(*label_selectors):
    logging.info(f"Getting namespaces based on label selectors: {label_selectors}")
    try:
        v1 = client.CoreV1Api()
        ns_set = set()
        if not label_selectors or len(label_selectors) == 0:
            api_response = v1.list_namespace()
            for ns in api_response.items:
                ns_set.add(ns.metadata.name)
        else:
            for label_selector in label_selectors:
                api_response = v1.list_namespace(label_selector=label_selector)
                for ns in api_response.items:
                    ns_set.add(ns.metadata.name)
        ns_list = sorted(list(ns_set))
        total_ns = len(ns_list)
        return ns_list, total_ns
    except Exception as e:
        logging.error(f"Error getting namespaces based on label selectors: {e}")
        raise Exception("Error getting namespaces based on label selectors") from e

# Function to get the helm releases in a namespace    
@cached(cache)    
def get_helm_releases_in_the_namespace(namespace):
    logging.info(f"Getting helm releases in namespace {namespace}")
    try:
        helm_release_list_json = subprocess.check_output(["helm", "list", "--namespace", namespace, "-o", "json"])
        helm_release_list = json.loads(helm_release_list_json)
        return helm_release_list
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting helm releases in namespace {namespace}: {str(e)}")

# Function to get the helm release history        
#@cached(cache)      
def get_helm_release_history(namespace, release_name):
    logging.info(f"Getting helm release history for {release_name} in namespace {namespace}")
    try:
        helm_release_history = subprocess.check_output(["helm", "history", release_name, "--namespace", namespace, "-o", "json"])
        helm_release_history = json.loads(helm_release_history)
        revisions = []
        for revision in helm_release_history:
            revision_number = revision['revision']
            updated = revision['updated']
            status = revision['status']
            chart = revision['chart']
            app_version = revision['app_version']
            description = revision['description']
            revisions.append((revision_number, updated, status, chart, app_version, description))
        return revisions
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting helm release history for {release_name} in namespace {namespace}: {str(e)}")

# Function to get the helm release values
#@cached(cache)    
def get_helm_release_values(namespace, release_name):
    logging.info(f"Getting helm release values for {release_name} in namespace {namespace}")
    try:
        process = subprocess.Popen(["helm", "get", "values", release_name, "--namespace", namespace, "-o", "yaml"], stdout=subprocess.PIPE)
        helm_release_values, _ = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        helm_release_values = helm_release_values.decode('utf-8')
        return helm_release_values
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting helm release values for {release_name} in namespace {namespace}: {str(e)}")
        
#@cached(cache)
def get_helm_release_manifest(namespace, release_name):
    logging.info(f"Getting helm release manifest for {release_name} in namespace {namespace}")
    try:
        process = subprocess.Popen(["helm", "get", "manifest", release_name, "--namespace", namespace], stdout=subprocess.PIPE)
        helm_release_manifest, _ = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        helm_release_manifest = helm_release_manifest.decode('utf-8')
        return helm_release_manifest
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting helm release manifest for {release_name} in namespace {namespace}: {str(e)}")

# Warmup function to keep the app alive
    

# Helper function to get the release data for a namespace
@cached(cache)
def get_release_data(ns):
    helm_releases = get_helm_releases_in_the_namespace(ns)
    result = []
    for release in helm_releases:
        if release['status'].lower() == "deployed":
            release_status_color = "green"
        elif release['status'].lower() == "failed":
            release_status_color = "red"
        else:
            release_status_color = "yellow"
        result.append((ns, release['name'], release['status'], release['chart'], release['app_version'], release_status_color))
    return result

def warmup():
    logging.info('Starting warmup')
    try:
        # Send a request to the home page
        response = requests.get('http://localhost:' + str(app_port) + '/')
        if response.status_code == 200:
            logging.info(f"Warmup successful")
        else:
            logging.info('Warmup failed with status code:', response.status_code)
    except Exception as e:
        logging.error('Warmup failed with exception:', e)

# Route to the home page with list of all releases selected by the label selectors
@app.route('/', methods=['GET'])
def home():
    start_time = time.time()
    ns_list, total_ns = get_namespace_names_based_on_either_label(*selectors_list)

    # Use ThreadPoolExecutor to process the namespaces in parallel
    with ThreadPoolExecutor(max_workers=40) as executor:
        release_data = list(executor.map(get_release_data, ns_list))

    # Flatten the list of lists
    release_data = [item for sublist in release_data for item in sublist]
    
    # Get the sort parameters from the request
    sort_attribute = request.args.get('sort_attribute', session.get('sort_attribute', '0'))
    sort_order = request.args.get('sort_order', session.get('sort_order', 'asc'))

    # Reverse the sort order if the same column is sorted again
    if session.get('sort_attribute') == sort_attribute:
        sort_order = 'desc' if sort_order == 'asc' else 'asc'
    else:
        # If the user clicked a different column, sort in ascending order
        sort_order = 'asc'

    # Sort the data
    reverse = sort_order == 'desc'
    release_data = sorted(release_data, key=lambda x: x[int(sort_attribute)], reverse=reverse)

    # Store the current sort attribute and order in the session
    session['sort_attribute'] = sort_attribute
    session['sort_order'] = sort_order    

    # Get the filter parameters from the request
    filter_namespace = request.args.get('filter_namespace', session.get('filter_namespace', ''))
    filter_release = request.args.get('filter_release', session.get('filter_release', ''))
    filter_status = request.args.get('filter_status', session.get('filter_status', ''))

    # Store the current filter parameters in the session
    session['filter_namespace'] = filter_namespace
    session['filter_release'] = filter_release
    session['filter_status'] = filter_status

    # If the filter parameters are specified, filter the release_data
    if filter_namespace:
        release_data = [release for release in release_data if filter_namespace.lower() in release[0].lower()]
    if filter_release:
        release_data = [release for release in release_data if filter_release.lower() in release[1].lower()]
    if filter_status:
        release_data = [release for release in release_data if filter_status.lower() in release[2].lower()]        

    total_releases = len(release_data)
    total_failed_releases = len([release for release in release_data if release[2] == "failed"])
    total_successful_releases = len([release for release in release_data if release[2] == "deployed"])
    all_other_releases = len([release for release in release_data if release[2] != "deployed" and release[2] != "failed"])
    
    return render_template(
                           'home.html', 
                           release_data=release_data, 
                           environment=environment, 
                           total_namespaces=total_ns, 
                           total_releases=total_releases, 
                           total_failed_releases=total_failed_releases, 
                           total_successful_releases=total_successful_releases, 
                           all_other_releases=all_other_releases
                          )
# Route to get the revision history of a selected release
@app.route('/revision/<namespace>/<release_name>')
def revision_history(namespace, release_name):
    # Get the revision history for the release
    revision_history = get_helm_release_history(namespace, release_name)
    return render_template('revision_history.html', revision_history=revision_history, release_name=release_name, namespace=namespace)

# Route to get the values of a selected release
@app.route('/values/<namespace>/<release_name>')
def release_values(namespace, release_name):
    release_values = get_helm_release_values(namespace, release_name)
    return render_template('release_values.html', release_values=release_values, release_name=release_name, namespace=namespace)

# Route to get the manifest of a selected release
@app.route('/manifest/<namespace>/<release_name>')
def release_manifest(namespace, release_name):
    release_manifest = get_helm_release_manifest(namespace, release_name)
    return render_template('release_manifest.html', release_manifest=release_manifest, release_name=release_name, namespace=namespace)

# Route to clear the cache
@app.route('/clear_cache', methods=['GET'])
def clear_cache():
    cache.clear()
    return redirect(url_for('home'))

# Route to reset the filter
@app.route('/reset_filter', methods=['GET'])
def reset_filter():
    # Clear the filter parameters from the session
    session.pop('filter_namespace', None)
    session.pop('filter_release', None)
    session.pop('filter_status', None)

    # Redirect to the home function
    return redirect(url_for('home'))

# Route for health check
@app.route('/healthz', methods=['GET'])
def healthz():
    return "OK"

# Error handler for server errors
@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return render_template('error.html', error_message=str(e)), 500

# Error handler for NameError
@app.errorhandler(NameError)
def handle_name_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return render_template('error.html', error_message=str(e)), 500

# Error handler for Exception
@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return render_template('error.html', error_message=str(e)), 500

# Error handler for subprocess.CalledProcessError
@app.errorhandler(subprocess.CalledProcessError)
def handle_subprocess_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return render_template('error.html', error_message=str(e)), 500

# Error handler for page not found
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Create a background scheduler to keep the app alive
scheduler = BackgroundScheduler()
# Run warmup immediately
scheduler.add_job(warmup, 'date', run_date=datetime.datetime.now())  # This will run immediately
scheduler.add_job(warmup, 'interval', seconds=app_warmup_interval)
scheduler.start()

# Run the app            
if __name__ == '__main__':
    # Start the warmup thread
    app.run(debug=True, port=app_port)
    
