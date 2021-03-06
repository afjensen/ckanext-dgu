﻿from setuptools import setup, find_packages

from ckanext.dgu import __version__

setup(
    name='ckanext-dgu',
    version=__version__,
    long_description="""\
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    namespace_packages=['ckanext', 'ckanext.dgu'],
    zip_safe=False,
    author='Cabinet Office, Open Knowledge Foundation',
    author_email='david.read@hackneyworkshop.com',
    license='AGPL',
    url='http://data.gov.uk/',
    description='CKAN DGU extensions',
    keywords='data packaging component tool server',
    install_requires=[
        # List of dependencies is moved to pip-requirements.txt
        # to avoid conflicts with Debian packaging.
        #'swiss',
        #'ckanclient>=0.5',
        #'ckanext', when it is released
    ],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
        [nose.plugins]
        pylons = pylons.test:PylonsPlugin

        [ckan.plugins]
        dgu_form = ckanext.dgu.plugin:DguForm
        dgu_drupal_auth = ckanext.dgu.plugin:DrupalAuthPlugin
        dgu_auth_api = ckanext.dgu.plugin:AuthApiPlugin
        dgu_publishers = ckanext.dgu.plugin:PublisherPlugin
        dgu_theme = ckanext.dgu.plugin:ThemePlugin
        dgu_search = ckanext.dgu.plugin:SearchPlugin
        dgu_publisher_form = ckanext.dgu.forms.publisher_form:PublisherForm
        dgu_dataset_form = ckanext.dgu.forms.dataset_form:DatasetForm
        dgu_mock_drupal2 = ckanext.dgu.testtools.mock_drupal2:MockDrupal2
        dgu_api = ckanext.dgu.plugin:ApiPlugin
        dgu_resource_updates = ckanext.dgu.plugin:ResourceModificationPlugin
        dgu_resource_url_updates = ckanext.dgu.plugin:ResourceURLModificationPlugin
        

        [console_scripts]
        ons_loader = ckanext.dgu.ons.command:load
        cospread_loader = ckanext.dgu.cospread:load
        change_licenses = ckanext.dgu.bin.change_licenses_cmd:command
        transfer_url = ckanext.dgu.bin.transfer_url_cmd:command
        ons_analysis = ckanext.dgu.bin.ons_analysis_cmd:command
        ofsted_fix = ckanext.dgu.bin.ofsted_fix_cmd:command
        publisher_migration = ckanext.dgu.bin.publisher_migration:command
        metadata_v3_migration = ckanext.dgu.bin.metadata_v3_migration:command
        generate_test_organisations = ckanext.dgu.testtools.organisations:command
        ons_remove_resources = ckanext.dgu.bin.ons_remove_resources:command
        ons_remove_packages = ckanext.dgu.bin.ons_remove_packages:command
        ons_delete_resourceless_packages = ckanext.dgu.bin.ons_delete_resourceless_packages:command
        ons_uksa_data4nr = ckanext.dgu.bin.ons_uksa_data4nr:command
        ons_merge_duplicates = ckanext.dgu.bin.ons_merge_duplicates:command
        last_mod_init = ckanext.dgu.bin.initial_last_major_modification:command
        dump_analysis = ckanext.dgu.bin.dump_analysis:command
        gov_daily = ckanext.dgu.bin.gov_daily:command
        sync_organisations = ckanext.dgu.bin.sync_organisations:command

        [ckan.forms]
        package_gov3 = ckanext.dgu.forms.package_gov3:get_gov3_fieldset

        [curate.actions]
        report=ckanext.dgu.curation:report

        [paste.paster_command]
        mock_drupal = ckanext.dgu.testtools.mock_drupal:Command
        create-test-data=ckanext.dgu.lib.cli:DguCreateTestDataCommand
        prod = ckanext.dgu.testtools.prodder:ProdCommand
        uklpreports = ckanext.dgu.lib.reports_uklp:UKLPReports
        wdtk_publisher_match = ckanext.dgu.commands.wdtk2:PublisherMatch
        update_licenses = ckanext.dgu.commands.license_updates:UpdateLicense
        scrape_resources = ckanext.dgu.bin.scrape_resources:ScrapeResources
        ons_scrape = ckanext.dgu.bin.ons_scraper:ONSUpdateTask
        selenium_tests = ckanext.dgu.commands.selenium_tests:TestRunner
        build_void = ckanext.dgu.commands.void_constructor:VoidConstructor
        stress_solr = ckanext.dgu.commands.solr_stress:SolrStressTest
        remap_govuk_resources = ckanext.dgu.commands.remap_govuk_resources:ResourceRemapper
        derive_govuk_resources = ckanext.dgu.commands.derive_govuk_resources:GovUkResourceChecker        
    """,
    test_suite = 'nose.collector',
)
