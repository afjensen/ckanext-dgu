import datetime
import logging
import csv
import StringIO

from webhelpers.text import truncate

from ckan.lib.base import model, abort, response, h, BaseController, request
from ckan.controllers.api import ApiController
from ckan.lib.helpers import OrderedDict, date_str_to_datetime, markdown_extract, json
from ckanext.dgu.plugins_toolkit import get_action
import ckan.plugins.toolkit as t
from ckanext.dgu.lib.helpers import is_sysadmin
from ckanext.dgu.lib import reports

log = logging.getLogger(__name__)

default_limit = 10

class DguApiController(ApiController):
    def latest_datasets(self):
        '''Designed for the dgu home page, shows lists the latest datasets
        that got changed (exluding extra, group and tag changes) with lots
        of details about each dataset.
        '''
        try:
            limit = int(request.params.get('limit', default_limit))
        except ValueError:
            limit = default_limit

        limit = min(100, limit) # max value
        query = model.Session.query(model.PackageRevision)
        query = query.filter(model.PackageRevision.state=='active')
        query = query.filter(model.PackageRevision.current==True)
        
        query = query.order_by(model.package_revision_table.c.revision_timestamp.desc())
        query = query.limit(limit)
        pkg_dicts = []
        for pkg_rev in query:
            pkg = pkg_rev.continuity
            publishers = pkg.get_groups('publisher')
            if publishers:
                pub_title = publishers[0].title
                pub_link = '/publisher/%s' % publishers[0].name
            else:
                pub_title = pub_link = None
            pkg_dict = OrderedDict((
                ('name', pkg.name),
                ('title', pkg.title),
                ('notes', pkg.notes),
                ('dataset_link', '/dataset/%s' % pkg.name),
                ('publisher_title', pub_title),
                ('publisher_link', pub_link),
                ('metadata_modified', pkg.extras.get('last_major_modification')),
                ))
            pkg_dicts.append(pkg_dict)
        return self._finish_ok(pkg_dicts)

    def revisions(self):
        '''
        Similar to the revision search API, lists all revisions for which
        a dataset or group changed in some way.

        URL Params:
          since-revision-id
          since-timestamp (utc)
          in-the-last-x-minutes
        '''
        # parse options
        rev_id = request.params.get('since-revision-id')
        since_timestamp = request.params.get('since-timestamp')
        in_the_last_x_minutes = request.params.get('in-the-last-x-minutes')
        now = datetime.datetime.utcnow()
        if rev_id is not None:
            rev = model.Session.query(model.Revision).get(rev_id)
            if not rev:
                abort(400, 'Revision ID "%s" does not exist' % rev_id)
            since_timestamp = rev.timestamp
        elif since_timestamp is not None:
            try:
                since_timestamp = date_str_to_datetime(since_timestamp)
            except (ValueError, TypeError), inst:
                example = now.strftime('%Y-%m-%d%%20%H:%M') # e.g. 2013-11-30%2023:15
                abort(400, 'Could not parse timestamp "%s": %s. Must be UTC. Example: since-time=%s' % (since_timestamp, inst, example))
        elif in_the_last_x_minutes is not None:
            try:
                in_the_last_x_minutes = int(in_the_last_x_minutes)
            except ValueError, inst:
                abort(400, 'Could not parse number of minutes "%s"' % in_the_last_x_minutes)
            since_timestamp = now - \
                         datetime.timedelta(minutes=in_the_last_x_minutes)
        else:
            abort(400, 'Must specify revisions parameter. It must be one from: since-revision-id since-timestamp in-the-last-x-minutes')

        # limit is higher if sysadmin
        if is_sysadmin():
            max_limit = 1000
        else:
            max_limit = 50

        # Get the revisions in the requested time frame
        revs = model.Session.query(model.Revision) \
               .filter(model.Revision.timestamp >= since_timestamp) \
               .order_by(model.Revision.timestamp.asc()) \
               .limit(max_limit) \
               .all()
        result = OrderedDict((
            ('number_of_revisions', len(revs)),
            ('since_timestamp', since_timestamp.strftime('%Y-%m-%d %H:%M')),
            ('current_timestamp', now.strftime('%Y-%m-%d %H:%M')),
            ('since_revision_id', revs[0].id if revs else None),
            ('newest_revision_id', revs[-1].id if revs else None),
            ('results_limited', len(revs) == max_limit)))

        # See which packages have changed in the time frame
        changed_package_ids = set()
        query = model.Session.query(model.PackageRevision) \
                .join(model.Revision) \
                .filter(model.Revision.timestamp >= since_timestamp) \
                .limit(max_limit)
        if query.count() == max_limit:
            result['results_limited'] = True
        changed_package_ids.update([pkg_rev.id for pkg_rev in query.all()])

        if not result['results_limited']:
            for related_type in (model.PackageTagRevision,
                                 model.PackageExtraRevision):
                query = model.Session.query(related_type) \
                        .join(model.Revision) \
                        .filter(model.Revision.timestamp >= since_timestamp) \
                        .limit(max_limit)
                res = query.all()
                if len(res) == max_limit:
                    result['results_limited'] = True
                changed_package_ids.update([obj_rev.package_id \
                                            for obj_rev in res])

        if not result['results_limited']:
            query = model.Session.query(model.ResourceRevision) \
                    .join(model.Revision) \
                    .filter(model.Revision.timestamp >= since_timestamp) \
                    .join(model.ResourceGroup,
                          model.ResourceRevision.resource_group_id == model.ResourceGroup.id) \
                    .limit(max_limit)
            res = query.all()
            if len(res) == max_limit:
                result['results_limited'] = True
            changed_package_ids.update([obj_rev.resource_group.package_id \
                                        for obj_rev in res])

        if not result['results_limited']:
            query = model.Session.query(model.MemberRevision) \
                    .filter_by(table_name='package') \
                    .join(model.Revision) \
                    .filter(model.Revision.timestamp >= since_timestamp) \
                    .limit(max_limit)
            res = query.all()
            if len(res) == max_limit:
                result['results_limited'] = True
            changed_package_ids.update([obj_rev.table_id for obj_rev in res])

        # due to corrupt old obj revision tables, some package_ids may be blank
        changed_package_ids.discard(None)

        result['datasets'] = [self._mini_pkg_dict(pkg_id) for pkg_id in changed_package_ids]
        return self._finish_ok(result)

    def _mini_pkg_dict(self, pkg_id):
        '''For a package id, return the basic details for the package in a
        dictionary.
        Quite expensive - does two database lookups - so be careful with running it
        lots of times.
        '''
        pkg = model.Session.query(model.Package).get(pkg_id)
        pubs = pkg.get_groups()
        pub = pubs[0] if pubs else None
        return OrderedDict((('id', pkg_id),
                            ('name', pkg.name),
                            ('title', pkg.title),
                            ('notes', markdown_extract(pkg.notes)),
                            ('dataset_link', '/dataset/%s' % pkg.name),
                            ('publisher_title', pub.title if pub else None),
                            ('publisher_link', '/publisher/%s' % pub.name if pub else None),
                            # Metadata modified is a big query, so leave out unless required
                            # ('metadata_modified', pkg.metadata_modified.isoformat()),
                            ))

    def dataset_count(self):
        from ckan.lib.search import SearchError
        try:
            # package search
            context = {'model': model, 'session': model.Session,
                       'user': 'visitor'}
            fq = 'capacity:"public"'
            data_dict = {
                'q':'',
                'fq':fq,
                'facet':'false',
                'rows':0,
                'start':0,
            }
            query = get_action('package_search')(context,data_dict)
            count = query['count']
        except SearchError, se:
            log.error('Search error: %s', se)
            count = 0

        return self._finish_ok(count)

class DguReportsController(ApiController):
    def organisation_resources(self, id, format='json'):
        #return json.dumps(reports.organisation_resources(id, date_formatter))
        include_sub_publishers = t.asbool(request.params.get('include_sub_publishers') or False)
        result = reports.organisation_resources(id,
            include_sub_organisations=include_sub_publishers,
            date_formatter=reports.british_date_formatter)
        if format == 'csv':
            filename = 'resources%s.csv' % (('_' + id) if id else '')
            response.headers['Content-Type'] = 'application/csv'
            response.headers['Content-Disposition'] = str('attachment; filename=%s' % (filename))
            return make_csv_from_dicts(result['rows'])
        else:
            response.headers['Content-Type'] = 'application/json'
            return json.dumps(result)

def make_csv_from_dicts(rows):
    csvout = StringIO.StringIO()
    csvwriter = csv.writer(
        csvout,
        dialect='excel',
        quoting=csv.QUOTE_NONNUMERIC
    )
    # extract the headers by looking at all the rows and
    # get a full list of the keys, retaining their ordering
    headers_ordered = []
    headers_set = set()
    for row in rows:
        new_headers = set(row.keys()) - headers_set
        headers_set |= new_headers
        for header in row.keys():
            if header in new_headers:
                headers_ordered.append(header)
    csvwriter.writerow(headers_ordered)
    for row in rows:
        items = []
        for header in headers_ordered:
            item = row.get(header, 'no record')
            if isinstance(item, datetime.datetime):
                item = item.strftime('%Y-%m-%d %H:%M')
            elif isinstance(item, (int, long, float)):
                item = unicode(item)
            elif item is None:
                item = ''
            else:
                item = item.encode('utf8')
            items.append(item)
        try:
            csvwriter.writerow(items)
        except Exception, e:
            raise Exception("%s: %s, %s"%(e, row, items))
    csvout.seek(0)
    return csvout.read()
