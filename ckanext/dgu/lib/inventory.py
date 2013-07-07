import os
import ckan.lib.munge as munge
from ckanext.dgu.plugins_toolkit import (c, NotAuthorized,
    ValidationError, get_action, check_access)
from ckan.lib.search import SearchIndexError

def render_inventory_template(writer):
    # Renders a template for completion by the department admin
    writer.writerow(["Dataset title",
                     "Description of dataset",
                     "Update frequency",
                     "Recommendation"])


def process_incoming_inventory_row(row_number, row, default_group_name):
    """
    Reads the provided row and updates the information found in the
    database where appropriate.

    The text of any exception raised will be shown to the user and the
    processing aborted.
    """
    from ckan import model

    publisher_name = default_group_name
    group = model.Group.get(publisher_name)
    title = row[0].value
    description = row[1].value
    frequency = row[2].value
    recommendation = row[3].value

    if not group:
        raise Exception("Unable to find the publisher {0}".format(publisher_name) )

    # First validation check, make sure we have enough to either update or create an
    # inventory item
    errors = []
    if not title.strip():
        errors.append("Dataset title")
    if not description.strip():
        errors.append("Description of dataset")

    if errors:
        raise Exception("The following fields were missing in row {0}: {1}".format(row_number, ",".join(errors)))

    # Check if we can find the dataset by title (for inventory items) and if so then check
    # for changes.
    pkg = model.Session.query(model.Package).filter(model.Package.title==title).first()
    if pkg:
        if pkg.extras.get('inventory', False):
            # Update the existing revision item.
            model.repo.new_revision()
            pkg.extras['frequency'] = frequency
            pkg.notes = description or pkg.notes
            pkg.extras['department-recommendation'] = recommendation
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

    package['groups'] = [{"name": publisher_name}]

    # Setup inventory specific items
    package['inventory'] = True
    package['frequency'] = frequency
    package['department-recommendation'] = recommendation

    try:
        pkg = get_action("package_create")(context, package)
    except NotAuthorized:
        raise Exception("Not authorised to create this dataset")
    except DataError:
        raise Exception("There was a problem with the integrity of the data")
    except SearchIndexError, e:
        raise Exception("Failed to add this dataset to search index")
    except ValidationError, e:
        raise Exception("There was an error validating the data: %s" % str(e))

    pkg = context['package']

    return (pkg, "Added",)

def render_inventory_header(writer):
    # Add
    #   - Reason for non-release
    writer.writerow(["Department ID", "Dataset title", "Description of dataset",
                     "Number of files", "Update frequency", "Status"])

def render_inventory_row(writer, datasets, group):
    """
    Writes out the provided inventory items to the provided writer in
    the correct format.
    """
    def encode(s):
        return s.encode('utf-8')

    for dataset in datasets:
        row = []
        row.append(encode(group.name))           # Group shortname
        row.append(encode(dataset.title))        # Dataset name
        row.append(encode(dataset.notes.strip() or "No description"))    # Dataset description
        row.append(str(len(dataset.resources)))  # Number of resources
        row.append(encode(unicode(dataset.extras.get('inventory',False))))
        row.append(encode(dataset.state))                   # Recommendation

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

