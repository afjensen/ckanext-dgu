import os
import ckan.lib.munge as munge
from ckanext.dgu.plugins_toolkit import (c, NotAuthorized, 
    ValidationError, get_action, check_access)


def process_incoming_inventory_row(row):
    """ 
    Reads the provided row and updates the information found in the 
    database where appropriate.

    The text of any exception raised will be shown to the user and the 
    processing aborted.
    """
    from ckan import model

    publisher_name = row[0].value
    title = row[1].value
    frequency = row[2].value
    description = row[3].value
    dataset_id = row[4].value

    # Validate the input!!

    # Check if dataset_id exists, and if so just return that we already have this dataset
    pkg = model.Package.get(dataset_id)
    print "Checking %s" % dataset_id
    if pkg:
        return (None, "",)

    # Check if we can find the dataset by title (for inventory items) and if so then check
    # for changes.
    pkg = model.Session.query(model.Package).filter(model.Package.title==title).first()
    if pkg:
        # Check inventory==false and if so DO NOT CONTINUE
        if pkg.extras.get('inventory', False):
            # Update the existing revision item.
            model.repo.new_revision()
            pkg.extras['frequency'] = frequency
            pkg.notes = description or pkg.notes

            # add extra fields and save
            model.Session.add(pkg)
            model.Session.commit()

            return (pkg, "Updated",)

    # Looks like a new inventory item, so we'll create a new one.
    context = {
        'model': model,
        'session': model.Session,
        'user': c.user,
        'allow_partial_update': True,
        'extras_as_string': True,
    }

    def get_clean_name(s):
        current = s
        counter = 1
        while True:
            current = munge.munge_title_to_name(current)
            if not model.Package.get(current):
                break
            current = "{0}_{1}".format(current,counter)
        return current

    #if not description:
    #    raise Exception("No description found for '{0}'".format(title))

    package = {}
    package["title"] = title
    package["name"] = get_clean_name(title)
    package["notes"] = description or " "
    package["access_constraints"] = "Not yet chosen"
    package["api_version"] = "3"    
    package['foi-email'] = "" 
    package['license_id']  = "" 
    package['foi-web'] = "" 
    package['contact-email'] = ""
    package['foi-name'] = ""
    package['contact-phone'] = ""
    package['contact-name'] = ""
    package['foi-phone'] = "" 
    package['theme-primary'] = ""

    package['group'] = publisher_name

    # Setup inventory specific items
    package['inventory'] = True
    package['economic-growth-score'] = 0
    package['social-growth-score'] = 0
    package['effective-public-services-score'] = 0
    package['connective-reference-data-score'] = 0            
    package['other-public-services-score'] = 0

    pkg = get_action("package_create")(context, package)
    pkg = context['package']

    return (pkg, "Added",)

def render_inventory_header(writer):
    # Add
    #   - Reason for non-release
    writer.writerow(["Department ID", "Dataset title", 
                     "Number of files", "Update frequency", 
                     "Description of dataset", "Dataset ID (internal use)"])

def render_inventory_row(writer, datasets, group):
    """
    Writes out the provided datasets to the provided writer in 
    the correct format.
    """
    def encode(s):
        return s.encode('utf-8')

    for dataset in datasets:
        row = []            
        row.append(encode(group.name))      # Group shortname
        row.append(encode(dataset.title))    # Dataset name
        row.append(str( len(dataset.resources)))
        row.append(encode(""))               # Frequency of update
        row.append(encode(dataset.notes or ""))    # Dataset description                

        row.append(encode(dataset.name))    # Dataset identifier                

        writer.writerow(row)      


class UploadFileHelper(object):
    """
    A contextmanager for handling file uploads by writing it to disk and 
    then returning the relevant file as a fileobj
    """
    def __init__(self, filename, file):
        self.input_file = file
        self.file_path = os.path.join('/tmp', filename)

    def __enter__(self):
        self.output_file = open(self.file_path, 'wb')
        self.input_file.seek(0)

        while True:
            data = self.input_file.read(-1)
            if not data:
                break
            self.output_file.write(data)
            self.output_file.flush()
        self.output_file.close()

        return open(self.file_path, "rb")

    def __exit__(self, type, value, traceback):
        try:
            os.unlink(self.file_path)        
        except:
            pass

        return not (type and value)

