from doajtest.helpers import DoajTestCase

from portality import models
from portality.formcontext import formcontext
from portality import lcc

from werkzeug.datastructures import MultiDict

from doajtest.fixtures import JournalFixtureFactory

JOURNAL_SOURCE = JournalFixtureFactory.make_journal_source()
JOURNAL_FORM = JournalFixtureFactory.make_journal_form()

JOURNAL_SOURCE_WITH_LEGACY_INFO = JournalFixtureFactory.make_journal_source_with_legacy_info()

#####################################################################
# Mocks required to make some of the lookups work
#####################################################################
@classmethod
def editor_group_pull(cls, field, value):
    eg = models.EditorGroup()
    eg.set_editor("eddie")
    eg.set_associates(["associate", "assan"])
    eg.set_name("Test Editor Group")
    return eg

mock_lcc_choices = [
    (u'H', u'Social Sciences'),
    (u'HB1-3840', u'--Economic theory. Demography')
]


def mock_lookup_code(code):
    if code == "H": return "Social Sciences"
    if code == "HB1-3840": return "Economic theory. Demography"
    return None


class TestManEdJournalReview(DoajTestCase):

    def setUp(self):
        super(TestManEdJournalReview, self).setUp()

        self.editor_group_pull = models.EditorGroup.pull_by_key
        models.EditorGroup.pull_by_key = editor_group_pull

        self.old_lcc_choices = lcc.lcc_choices
        lcc.lcc_choices = mock_lcc_choices

        self.old_lookup_code = lcc.lookup_code
        lcc.lookup_code = mock_lookup_code

    def tearDown(self):
        super(TestManEdJournalReview, self).tearDown()

        models.EditorGroup.pull_by_key = self.editor_group_pull
        lcc.lcc_choices = self.old_lcc_choices

        lcc.lookup_code = self.old_lookup_code

    def test_01_maned_review_success(self):
        """Give the Managing Editor's journal form a full workout"""

        # we start by constructing it from source
        fc = formcontext.JournalFormFactory.get_form_context(role="admin", source=models.Journal(**JOURNAL_SOURCE))
        assert isinstance(fc, formcontext.ManEdJournalReview)
        assert fc.form is not None
        assert fc.source is not None
        assert fc.form_data is None
        assert fc.template is not None

        # no need to check form rendering - there are no disabled fields

        # now construct it from form data (with a known source)
        fc = formcontext.JournalFormFactory.get_form_context(
            role="admin",
            form_data=MultiDict(JOURNAL_FORM),
            source=models.Journal(**JOURNAL_SOURCE)
        )

        assert isinstance(fc, formcontext.ManEdJournalReview)
        assert fc.form is not None
        assert fc.source is not None
        assert fc.form_data is not None

        # test each of the workflow components individually ...

        # pre-validate and ensure that the disabled fields get re-set
        fc.pre_validate()
        # no disabled fields, so just test the function runs

        # run the validation itself
        fc.form.subject.choices = mock_lcc_choices # set the choices allowed for the subject manually (part of the test)
        assert fc.validate(), fc.form.errors

        # run the crosswalk (no need to look in detail, xwalks are tested elsewhere)
        fc.form2target()
        assert fc.target is not None

        # patch the target with data from the source
        fc.patch_target()
        assert fc.target.created_date == "2000-01-01T00:00:00Z"
        assert fc.target.id == "abcdefghijk_journal"
        # everything else is overridden by the form, so no need to check it has patched

        # now do finalise (which will also re-run all of the steps above)
        fc.finalise()
        assert True # gives us a place to drop a break point later if we need it

    def test_02_maned_review_optional_validation(self):
        """Test optional validation in the Managing Editor's journal form"""

        # construct it from form data (with a known source)
        fc = formcontext.JournalFormFactory.get_form_context(
            role="admin",
            form_data=MultiDict(JOURNAL_FORM),
            source=models.Journal(**JOURNAL_SOURCE)
        )

        # do not re-test the form context

        # run the validation, but make it fail by omitting a required field
        fc.form.title.data = ''
        fc.form.subject.choices = mock_lcc_choices # set the choices allowed for the subject manually (part of the test)
        assert not fc.validate()

        # tick the optional validation box and try again
        fc.form.make_all_fields_optional.data = True
        assert fc.validate(), fc.form.errors

        # run the crosswalk, don't test it at all in this test
        fc.form2target()

        # patch the target with data from the source
        fc.patch_target()

        # right, so let's see if we managed to get a title-less journal from this
        assert fc.target.bibjson().title is None, fc.target.bibjson().title

    def test_03_maned_review_legacy_info(self):
        """Test legacy journal info display and saving in the Managing Editor's journal form"""

        # we start by constructing it from source
        fc = formcontext.JournalFormFactory.get_form_context(role="admin", source=models.Journal(**JOURNAL_SOURCE))
        # do not repeat tests on the form context, all that is tested above

        # construct it from form data (with a known source)
        fc = formcontext.JournalFormFactory.get_form_context(
            role="admin",
            form_data=MultiDict(JOURNAL_FORM),
            source=models.Journal(**JOURNAL_SOURCE_WITH_LEGACY_INFO)
        )

        # do not re-test the form context

        # check that we can render the form
        # FIXME: we can't easily render the template - need to look into Flask-Testing for this
        # html = fc.render_template(edit_journal=True)
        html = fc.render_field_group("old_journal_fields")
        assert html is not None
        assert html != ""

        # check the fields which we expect appear
        expected_fields = ["author_pays", "author_pays_url", "oa_end_year"]
        for ef in expected_fields:
            assert 'name="{0}"'.format(ef) in html, "expected field {0} not found in HTML".format(ef)

        # run the validation
        fc.form.subject.choices = mock_lcc_choices # set the choices allowed for the subject manually (part of the test)
        assert fc.validate(), fc.form.errors

        # run the crosswalk, don't test it at all in this test
        fc.form2target()

        # patch the target with data from the source
        fc.patch_target()

        # did we get the old info walked across?
        assert fc.target.bibjson().author_pays == JOURNAL_FORM['author_pays']
        assert fc.target.bibjson().author_pays_url == JOURNAL_FORM['author_pays_url']
        assert fc.target.bibjson().oa_end.get('year') == JOURNAL_FORM['oa_end_year']

    def test_04_maned_review_doaj_seal(self):
        """Test the seal checkbox on the maned review form"""

        # construct it from form data (with a known source)
        fc = formcontext.JournalFormFactory.get_form_context(
            role="admin",
            form_data=MultiDict(JOURNAL_FORM),
            source=models.Journal(**JOURNAL_SOURCE)
        )

        # set the seal to False using the form
        fc.form.doaj_seal.data = False

        # run the crosswalk, don't test it at all in this test
        fc.form2target()
        # patch the target with data from the source
        fc.patch_target()

        # ensure the model has seal set to False
        assert fc.target.has_seal() is False

        # Set the seal to True in the object and check the form reflects this
        fc.target.set_seal(True)
        fc.data2form()

        assert fc.form.doaj_seal.data is True
