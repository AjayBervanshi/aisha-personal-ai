import logging
import os
import requests
import psycopg2
from src.core.config import Config
from src.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

class HealthReport:
    def __init__(self):
        self.status = {}
        self.errors = []

    def add_check(self, name, passed, message=None):
        self.status[name] = passed
        if not passed and message:
            self.errors.append(message)

    def is_healthy(self):
        return all(self.status.values())

def check_environment_variables():
    required_env_vars = ['API_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'LOG_LEVEL']
    report = HealthReport()
    for var in required_env_vars:
        if var not in os.environ:
            report.add_check(var, False, f"Environment variable {var} is missing")
        else:
            report.add_check(var, True)
    return report

def check_api_connection():
    report = HealthReport()
    try:
        response = requests.get('https://api.example.com/healthcheck')
        report.add_check('API Connection', response.status_code == 200)
    except requests.exceptions.RequestException as e:
        report.add_check('API Connection', False, str(e))
    return report

def check_database_connection():
    report = HealthReport()
    try:
        conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME']
        )
        conn.close()
        report.add_check('Database Connection', True)
    except psycopg2.OperationalError as e:
        report.add_check('Database Connection', False, str(e))
    return report

def check_log_connection():
    report = HealthReport()
    try:
        logger.info('Log connection test')
        report.add_check('Log Connection', True)
    except Exception as e:
        report.add_check('Log Connection', False, str(e))
    return report

def perform_preflight_check():
    reports = [
        check_environment_variables(),
        check_api_connection(),
        check_database_connection(),
        check_log_connection()
    ]
    overall_report = HealthReport()
    for report in reports:
        for check, passed in report.status.items():
            overall_report.add_check(check, passed)
        overall_report.errors.extend(report.errors)
    if not overall_report.is_healthy():
        raise ConfigurationError('Preflight check failed', overall_report.errors)
    return overall_report

def main():
    try:
        report = perform_preflight_check()
        logger.info('Preflight check passed')
        print(report.status)
    except ConfigurationError as e:
        logger.error('Preflight check failed')
        print(e)

if __name__ == '__main__':
    main()