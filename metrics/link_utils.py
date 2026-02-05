import re
import urllib.parse as ur

AFFILIATES = {
    r"https://am.wikimedia.org/wiki/(.*)": "wmam",
    r"https://bd.wikimedia.org/wiki/(.*)": "wmbd",
    r"https://be.wikimedia.org/wiki/(.*)": "wmbe",
    r"https://br.wikimedia.org/wiki/(.*)": "wmbr",
    r"https://ca.wikimedia.org/wiki/(.*)": "wmca",
    r"https://cn.wikimedia.org/wiki/(.*)": "wmcn",
    r"https://co.wikimedia.org/wiki/(.*)": "wmco",
    r"https://dk.wikimedia.org/wiki/(.*)": "wmdk",
    r"https://ec.wikimedia.org/wiki/(.*)": "wmec",
    r"https://ee.wikimedia.org/wiki/(.*)": "wmee",
    r"https://fi.wikimedia.org/wiki/(.*)": "wmfi",
    r"https://ge.wikimedia.org/wiki/(.*)": "wmge",
    r"https://hi.wikimedia.org/wiki/(.*)": "wmhi",
    r"https://id.wikimedia.org/wiki/(.*)": "wmid",
    r"https://mitglieder.wikimedia.at/(.*)": "wmat",
    r"https://mk.wikimedia.org/wiki/(.*)": "wmmk",
    r"https://mx.wikimedia.org/wiki/(.*)": "wmmx",
    r"https://nl.wikimedia.org/wiki/(.*)": "wmnl",
    r"https://no.wikimedia.org/wiki/(.*)": "wmno",
    r"https://nyc.wikimedia.org/wiki/(.*)": "wmnyc",
    r"https://pa-us.wikimedia.org/wiki/(.*)": "wmpa-us",
    r"https://pl.wikimedia.org/wiki/(.*)": "wmpl",
    r"https://pt.wikimedia.org/wiki/(.*)": "wmpt",
    r"https://punjabi.wikimedia.org/wiki/(.*)": "wmpunjabi",
    r"https://romd.wikimedia.org/wiki/(.*)": "wmromd",
    r"https://rs.wikimedia.org/wiki/(.*)": "wmrs",
    r"https://ru.wikimedia.org/wiki/(.*)": "wmru",
    r"https://se.wikimedia.org/wiki/(.*)": "wmse",
    r"https://tr.wikimedia.org/wiki/(.*)": "wmtr",
    r"https://ua.wikimedia.org/wiki/(.*)": "wmua",
    r"https://ve.wikimedia.org/wiki/(.*)": "wmve",
    r"https://wiki.wikimedia.it/wiki/(.*)": "wmit",
    r"https://wikimedia.cl/(.*)": "wmcl",
    r"https://wikimedia.de/(.*)": "wmde",
    r"https://wikimedia.fr/(.*)": "wmfr",
    r"https://wikimedia.hu/wiki/(.*)": "wmhu",
    r"https://wikimedia.org.au/wiki/(.*)": "wmau",
    r"https://wikimedia.org.uk/wiki/(.*)": "wmuk",
    r"https://wikimedia.pl/(.*)": "wmplsite",
    r"https://wikimedia.sk/(.*)": "wmsk",
    r"https://wikimediadc.org/wiki/(.*)": "wmdc",
    r"https://www.wikimedia.ch/(.*)": "wmch",
    r"https://www.wikimedia.cz/(.*)": "wmcz",
    r"https://www.wikimedia.es/wiki/(.*)": "wmes",
    r"https://www.wikimedia.org.ar/wiki/(.*)": "wmar",
    r"https://www.wikimedia.org.il/(.*)": "wmil",
}

ARTICLES = {
    r"https://arxiv.org/abs/(.*)": "arxiv",
    r"https://diff.wikimedia.org/(.*)": "DiffBlog",
    r"https://doi.org/(.*)": "DOI",
    r"https://hdl.handle.net/(.*)": "hdl",
    r"https://scholar.google.com/scholar?q=(.*)": "Scholar",
    r"https://translatewiki.net/wiki/(.*)": "translatewiki",
    r"https://viaf.org/viaf/(.*)": "VIAF",
    r"https://wikiapiary.com/wiki/(.*)": "WikiApiary",
    r"https://www.google.com/search?q=(.*)": "Google",
    r"https://www.jstor.org/journals/(.*)": "JSTOR",
    r"https://pubmed.ncbi.nlm.nih.gov/(.*)": "PMID",
    r"https://www.worldcat.org/issn/(.*)": "ISSN",
}

FRIENDLY_PROJECTS = {
    r"https://archive.org/details/(.*)": "IArchive",
    r"https://creativecommons.org/(.*)": "ccorg",
    r"https://creativecommons.org/licenses/(.*)": "CreativeCommons",
    r"https://dashboard.wikiedu.org/(.*)": "wikiedudashboard",
    r"https://discord.com/(.*)": "discord",
    r"https://lingualibre.org/wiki/(.*)": "LinguaLibre",
    r"https://wiki.openstreetmap.org/wiki/(.*)": "OSMwiki",
    r"https://www.flickr.com/people/(.*)": "FlickrUser",
    r"https://www.flickr.com/photo.gne?id=(.*)": "FlickrPhoto",
}

LANGUAGE_BASED_PROJECTS = {
    r"https://(.*).wikibooks.org/wiki/(.*)": "b:",
    r"https://(.*).wikinews.org/wiki/(.*)": "n:",
    r"https://(.*).wikipedia.org/wiki/(.*)": "w:",
    r"https://(.*).wikiquote.org/wiki/(.*)": "q:",
    r"https://(.*).wikisource.org/wiki/(.*)": "s:",
    r"https://(.*).wikiversity.org/wiki/(.*)": "v:",
    r"https://(.*).wikivoyage.org/wiki/(.*)": "voy:",
    r"https://(.*).wiktionary.org/wiki/(.*)": "wikt:",
}

MAIN_PROJECTS = {
    r"https://commons.wikimedia.org/wiki/(.*)": "c",
    r"https://meta.wikimedia.org/wiki/(.*)": "",
    r"https://outreach.wikimedia.org/wiki/(.*)": "Outreach",
    r"https://phabricator.wikimedia.org/(.*)": "phab",
    r"https://species.wikimedia.org/wiki/(.*)": "species",
    r"https://wikitech.wikimedia.org/wiki/(.*)": "Wikitech",
    r"https://www.mediawiki.org/wiki/(.*)": "mw",
    r"https://www.wikidata.org/wiki/(.*)": "d",
    r"https://www.wikifunctions.org/wiki/(.*)": "Wikifunctions",
}

OTHER_WIKIMEDIA_PROJECTS = {
    r"https://beta.wikiversity.org/wiki/(.*)": "betawikiversity",
    r"https://bugzilla.wikimedia.org/(.*)": "MediaZilla",
    r"https://etherpad.wikimedia.org/(.*)": "Etherpad",
    r"https://foundation.wikimedia.org/wiki/(.*)": "WMF",
    r"https://gerrit.wikimedia.org/r/(.*)": "Gerrit",
    r"https://gitlab.wikimedia.org/(.*)": "gitlab",
    r"https://incubator.wikimedia.org/wiki/(.*)": "incubator",
    r"https://policy.wikimedia.org/(.*)": "Policy",
    r"https://quality.wikimedia.org/wiki/(.*)": "Quality",
    r"https://releases.wikimedia.org/(.*)": "download",
    r"https://spcom.wikimedia.org/wiki/(.*)": "spcom",
    r"https://stats.wikimedia.org/(.*)": "stats",
    r"https://strategy.wikimedia.org/wiki/(.*)": "strategy",
    r"https://test.wikidata.org/wiki/(.*)": "Testwikidata",
    r"https://test.wikipedia.org/wiki/(.*)": "Testwiki",
    r"https://test-commons.wikimedia.org/wiki/(.*)": "Testcommons",
    r"https://toolhub.wikimedia.org/(.*)": "toolhub",
    r"https://usability.wikimedia.org/wiki/(.*)": "usability",
    r"https://vote.wikimedia.org/wiki/(.*)": "Votewiki",
    r"https://wikimania.wikimedia.org/wiki/(.*)": "Wikimania",
    r"https://wikimediafoundation.org/(.*)": "foundation",
}

TOOLFORGE = {
    r"https://(.*).(toolforge).org/(.*)": "toolforge:",
    r"https://mix-n-match.toolforge.org/#/catalog/(.*)": "mixnmatch",
    r"https://outreachdashboard.wmflabs.org/(.*)": "wmfdashboard",
    r"https://petscan.wmflabs.org/?psid=(.*)": "petscan",
    r"https://public-paws.wmcloud.org/(.*)": "paws",
    r"https://quarry.wmcloud.org/(.*)": "Quarry",
    r"https://xtools.wmcloud.org/(.*)": "xtools",
}

INVERTED_AFFILIATES = {
    r"^wmam:(.*)": "https://am.wikimedia.org/wiki/$2",
    r"^wmbd:(.*)": "https://bd.wikimedia.org/wiki/$2",
    r"^wmbe:(.*)": "https://be.wikimedia.org/wiki/$2",
    r"^wmbr:(.*)": "https://br.wikimedia.org/wiki/$2",
    r"^wmca:(.*)": "https://ca.wikimedia.org/wiki/$2",
    r"^wmcn:(.*)": "https://cn.wikimedia.org/wiki/$2",
    r"^wmco:(.*)": "https://co.wikimedia.org/wiki/$2",
    r"^wmdk:(.*)": "https://dk.wikimedia.org/wiki/$2",
    r"^wmec:(.*)": "https://ec.wikimedia.org/wiki/$2",
    r"^wmee:(.*)": "https://ee.wikimedia.org/wiki/$2",
    r"^wmfi:(.*)": "https://fi.wikimedia.org/wiki/$2",
    r"^wmge:(.*)": "https://ge.wikimedia.org/wiki/$2",
    r"^wmhi:(.*)": "https://hi.wikimedia.org/wiki/$2",
    r"^wmid:(.*)": "https://id.wikimedia.org/wiki/$2",
    r"^wmat:(.*)": "https://mitglieder.wikimedia.at/$2",
    r"^wmmk:(.*)": "https://mk.wikimedia.org/wiki/$2",
    r"^wmmx:(.*)": "https://mx.wikimedia.org/wiki/$2",
    r"^wmnl:(.*)": "https://nl.wikimedia.org/wiki/$2",
    r"^wmno:(.*)": "https://no.wikimedia.org/wiki/$2",
    r"^wmnyc:(.*)": "https://nyc.wikimedia.org/wiki/$2",
    r"^wmpa-us:(.*)": "https://pa-us.wikimedia.org/wiki/$2",
    r"^wmpl:(.*)": "https://pl.wikimedia.org/wiki/$2",
    r"^wmpt:(.*)": "https://pt.wikimedia.org/wiki/$2",
    r"^wmpunjabi:(.*)": "https://punjabi.wikimedia.org/wiki/$2",
    r"^wmromd:(.*)": "https://romd.wikimedia.org/wiki/$2",
    r"^wmrs:(.*)": "https://rs.wikimedia.org/wiki/$2",
    r"^wmru:(.*)": "https://ru.wikimedia.org/wiki/$2",
    r"^wmse:(.*)": "https://se.wikimedia.org/wiki/$2",
    r"^wmtr:(.*)": "https://tr.wikimedia.org/wiki/$2",
    r"^wmua:(.*)": "https://ua.wikimedia.org/wiki/$2",
    r"^wmve:(.*)": "https://ve.wikimedia.org/wiki/$2",
    r"^wmit:(.*)": "https://wiki.wikimedia.it/wiki/$2",
    r"^wmcl:(.*)": "https://wikimedia.cl/$2",
    r"^wmde:(.*)": "https://wikimedia.de/$2",
    r"^wmfr:(.*)": "https://wikimedia.fr/$2",
    r"^wmhu:(.*)": "https://wikimedia.hu/wiki/$2",
    r"^wmau:(.*)": "https://wikimedia.org.au/wiki/$2",
    r"^wmuk:(.*)": "https://wikimedia.org.uk/wiki/$2",
    r"^wmplsite:(.*)": "https://wikimedia.pl/$2",
    r"^wmsk:(.*)": "https://wikimedia.sk/$2",
    r"^wmdc:(.*)": "https://wikimediadc.org/wiki/$2",
    r"^wmch:(.*)": "https://www.wikimedia.ch/$2",
    r"^wmcz:(.*)": "https://www.wikimedia.cz/$2",
    r"^wmes:(.*)": "https://www.wikimedia.es/wiki/$2",
    r"^wmar:(.*)": "https://www.wikimedia.org.ar/wiki/$2",
    r"^wmil:(.*)": "https://www.wikimedia.org.il/$2",
}

INVERTED_ARTICLES = {
    r"^arxiv:(.*)": "https://arxiv.org/abs/$2",
    r"^DiffBlog:(.*)": "https://diff.wikimedia.org/$2",
    r"^DOI:(.*)": "https://doi.org/$2",
    r"^hdl:(.*)": "https://hdl.handle.net/$2",
    r"^Scholar:(.*)": "https://scholar.google.com/scholar?q=$2",
    r"^translatewiki:(.*)": "https://translatewiki.net/wiki/$2",
    r"^VIAF:(.*)": "https://viaf.org/viaf/$2",
    r"^WikiApiary:(.*)": "https://wikiapiary.com/wiki/$2",
    r"^Google:(.*)": "https://www.google.com/search?q=$2",
    r"^JSTOR:(.*)": "https://www.jstor.org/journals/$2",
    r"^PMID:(.*)": "https://www.ncbi.nlm.nih.gov/pubmed/$2?dopt=Abstract",
    r"^ISSN:(.*)": "https://www.worldcat.org/issn/21",
}

INVERTED_FRIENDLY_PROJECTS = {
    r"^IArchive:(.*)": "https://archive.org/details/$2",
    r"^ccorg:(.*)": "https://creativecommons.org/$2",
    r"^CreativeCommons:(.*)": "https://creativecommons.org/licenses/$2",
    r"^wikiedudashboard:(.*)": "https://dashboard.wikiedu.org/$2",
    r"^LinguaLibre:(.*)": "https://lingualibre.org/wiki/$2",
    r"^OSMwiki:(.*)": "https://wiki.openstreetmap.org/wiki/$2",
    r"^FlickrUser:(.*)": "https://www.flickr.com/people/$2",
    r"^FlickrPhoto:(.*)": "https://www.flickr.com/photo.gne?id=$2",
    r"^Discord:(.*)": "https://discord.com/$2",
}

INVERTED_LANGUAGE_BASED_PROJECTS = {
    r"^b:(.*):(.*)": "https://$1.wikibooks.org/wiki/$2",
    r"^n:(.*):(.*)": "https://$1.wikinews.org/wiki/$2",
    r"^w:(.*):(.*)": "https://$1.wikipedia.org/wiki/$2",
    r"^q:(.*):(.*)": "https://$1.wikiquote.org/wiki/$2",
    r"^s:(.*):(.*)": "https://$1.wikisource.org/wiki/$2",
    r"^v:(.*):(.*)": "https://$1.wikiversity.org/wiki/$2",
    r"^voy:(.*):(.*)": "https://$1.wikivoyage.org/wiki/$2",
    r"^wikt:(.*):(.*)": "https://$1.wiktionary.org/wiki/$2",
}

INVERTED_MAIN_PROJECTS = {
    r"^c:(.*)": "https://commons.wikimedia.org/wiki/$2",
    r"^outreach:(.*)": "https://outreach.wikimedia.org/wiki/$2",
    r"^phab:(.*)": "https://phabricator.wikimedia.org/$2",
    r"^species:(.*)": "https://species.wikimedia.org/wiki/$2",
    r"^wikitech:(.*)": "https://wikitech.wikimedia.org/wiki/$2",
    r"^mw:(.*)": "https://www.mediawiki.org/wiki/$2",
    r"^d:(.*)": "https://www.wikidata.org/wiki/$2",
    r"^wikifunctions:(.*)": "https://www.wikifunctions.org/wiki/$2",
}

INVERTED_OTHER_WIKIMEDIA_PROJECTS = {
    r"^betawikiversity:(.*)": "https://beta.wikiversity.org/wiki/$2",
    r"^MediaZilla:(.*)": "https://bugzilla.wikimedia.org/$2",
    r"^Etherpad:(.*)": "https://etherpad.wikimedia.org/$2",
    r"^WMF:(.*)": "https://foundation.wikimedia.org/wiki/$2",
    r"^Gerrit:(.*)": "https://gerrit.wikimedia.org/r/$2",
    r"^gitlab:(.*)": "https://gitlab.wikimedia.org/$2",
    r"^incubator:(.*)": "https://incubator.wikimedia.org/wiki/$2",
    r"^Policy:(.*)": "https://policy.wikimedia.org/$2",
    r"^Quality:(.*)": "https://quality.wikimedia.org/wiki/$2",
    r"^download:(.*)": "https://releases.wikimedia.org/$2",
    r"^spcom:(.*)": "https://spcom.wikimedia.org/wiki/$2",
    r"^stats:(.*)": "https://stats.wikimedia.org/$2",
    r"^strategy:(.*)": "https://strategy.wikimedia.org/wiki/$2",
    r"^Testwikidata:(.*)": "https://test.wikidata.org/wiki/$2",
    r"^Testwiki:(.*)": "https://test.wikipedia.org/wiki/$2",
    r"^Testcommons:(.*)": "https://test-commons.wikimedia.org/wiki/$2",
    r"^toolhub:(.*)": "https://toolhub.wikimedia.org/$2",
    r"^usability:(.*)": "https://usability.wikimedia.org/wiki/$2",
    r"^Votewiki:(.*)": "https://vote.wikimedia.org/wiki/$2",
    r"^Wikimania:(.*)": "https://wikimania.wikimedia.org/wiki/$2",
    r"^foundation:(.*)": "https://wikimediafoundation.org/$2",
}

INVERTED_TOOLFORGE = {
    r"^toolforge:([^\/]+)\/(.+)": "https://$1.toolforge.org/$2",
    r"^mixnmatch:(.*)": "https://mix-n-match.toolforge.org/#/catalog/$2",
    r"^wmfdashboard:(.*)": "https://outreachdashboard.wmflabs.org/$2",
    r"^petscan:(.*)": "https://petscan.wmflabs.org/?psid=$2",
    r"^paws:(.*)": "https://public-paws.wmcloud.org/$2",
    r"^Quarry:(.*)": "https://quarry.wmcloud.org/$2",
    r"^xtools:(.*)": "https://xtools.wmcloud.org/$2",
}

PATTERNS = (
    AFFILIATES
    | ARTICLES
    | FRIENDLY_PROJECTS
    | LANGUAGE_BASED_PROJECTS
    | MAIN_PROJECTS
    | OTHER_WIKIMEDIA_PROJECTS
    | TOOLFORGE
)

INVERTED_PATTERNS = (
    INVERTED_AFFILIATES
    | INVERTED_ARTICLES
    | INVERTED_FRIENDLY_PROJECTS
    | INVERTED_LANGUAGE_BASED_PROJECTS
    | INVERTED_MAIN_PROJECTS
    | INVERTED_OTHER_WIKIMEDIA_PROJECTS
    | INVERTED_TOOLFORGE
)


def process_all_references(input_string):
    """
    Gets the input_string of the done activities of a metric and dewikify all the references listed.
    All the references are in the format <ref name="sara-123">XYZ</ref>.
    """
    updated_references = []
    re.sub(
        r'<ref name="sara-\d+">.*?</ref>',
        lambda match: unwikify_link(match, updated_references),
        input_string,
    )
    return updated_references


def unwikify_link(match, updated_references):
    """
    Receives a match for a reference and makes it into a html element.
    """

    link = match.group(0)

    # Get the Reference ID
    match_ref = re.search(r'<ref name="sara-(\d+)">(.*)</ref>', link)

    if match_ref:
        ref_id = match_ref.group(1)
        ref_content = match_ref.group(2)
        updated_content = replace_with_links(
            ref_content
        )  # Process the ref tag inner part
        if "bulleted list" in updated_content:
            bl_match = re.match(r"(.*)\{\{bulleted list\|(.*)\}\}(.*)", updated_content)
            if bl_match:
                bullet_items = bl_match.group(2).split("|")
                # Make the concatenation of the bulleted list as an HTML element
                updated_content = (
                    bl_match.group(1)
                    + "<ul>\n"
                    + "\n".join(f"<li>{item}</li>" for item in bullet_items)
                    + "\n</ul>"
                    + bl_match.group(3)
                )
        updated_link = f'<li id="sara-{ref_id}">{ref_id}. {updated_content}</li>'

        updated_references.append(updated_link)
        return updated_link
    return link


def replace_with_links(input_string):
    def replace(match):
        substring = match.group(0)

        if substring.startswith("[[") and substring.endswith("]]"):
            content = substring[2:-2]
            meta = False
            if "|" in content:
                link, friendly = content.split("|", 1)
                if ":" not in link:
                    meta = True
                elif any(
                    link.startswith(item)
                    for item in [
                        "Media:",
                        "Special:",
                        "User:",
                        "Project:",
                        "File:",
                        "MediaWiki:",
                        "Template:",
                        "Help:",
                        "Category:",
                    ]
                ):
                    meta = True
            else:
                link = friendly = content
                meta = True

            link = ur.quote(dewikify_url(link.replace(" ", "_"), meta), safe=":/")
            return f'<a target="_blank" href="{link}">{friendly}</a>'
        elif substring.startswith("[") and substring.endswith("]"):
            content = substring[1:-1]
            if " " in content:
                link, friendly = content.split(" ", 1)
            else:
                link = friendly = content
            return f'<a target="_blank" href="{link}">{friendly}</a>'

    result = re.sub(r"(\[\[.*?\]\]|\[.*?\])", replace, input_string)
    return result


def dewikify_url(link, meta=False):
    for pattern, prefix in INVERTED_PATTERNS.items():
        match = re.match(pattern, link)
        if match:
            number_of_groups = len(match.groups())
            lang = ""
            if number_of_groups == 2:
                lang = match.group(1)
                page = match.group(2)
            else:
                page = match.group(1)

            page = ur.unquote(page)
            clean_page = page.replace("_", " ")
            clean_page = clean_page[:-1] if clean_page.endswith("/") else clean_page

            return prefix.replace("$1", f"{lang}").replace("$2", f"{clean_page}")

    # The link is a meta link, so no prefix
    if meta:
        return f"https://meta.wikimedia.org/wiki/{link}"
    else:  # The link is not a proper Wiki link
        return f"{link}" if link != "-" else ""


# ======================================================================================================================
# PROCESS OF SAVING THE REFERENCE TEXT TO THE REPORT INSTANCE
# ======================================================================================================================
# 1. receive and wikify the links field (deal with external and internal links, including from mapped projects)
# 2. create the reference text
# ======================================================================================================================
def wikify_link(link):
    """
    Receives a URL link and tries to wikify it, based on the patterns and correspondences.
    There are 4 scenarios for the return:
    1. The link is a simple non-Wiki URL, in which case, it returns the link as an external wikitext link, i.e. [link]
    2. The link is a mapped URL and from a non-language based Wikimedia project, in which case, it returns the link as an internal wikitext link, i.e. [[project:page|page]]
    3. The link is a mapped URL and from a language based Wikimedia project, in which case, it returns the link as an internal wikitext link, i.e. [[project:language:page|page]]
    4. The link is a mapped URL and from toolforge, in which case, it returns the link as an internal wikitext link, i.e. [[toolforge:project:page|page]]
    """
    for pattern, prefix in PATTERNS.items():
        match = re.match(pattern, link)
        if match:
            number_of_groups = len(match.groups())
            project = ""
            lang = ""
            if number_of_groups == 3:
                project = match.group(1)
                page = match.group(3)
            elif number_of_groups == 2:
                lang = match.group(1)
                page = match.group(2)
            else:
                page = match.group(1)

            page = ur.unquote(page)
            clean_page = page.replace("_", " ")
            clean_page = clean_page[:-1] if clean_page.endswith("/") else clean_page

            return (
                f"[[{prefix}{project}/{page}|{clean_page}]]"
                if project
                else f"[[{prefix}{lang}:{page}|{clean_page}]]"
            )

    return f"[{link}]" if link != "-" else ""


def build_wiki_ref(links, report_id):
    links = links.replace("\\r\\n", "\r\n").splitlines()
    formatted_links = []
    for link in links:
        formatted_links.append(wikify_link(link))

    ref_content = ", ".join(formatted_links)
    if ref_content:
        return f'<ref name="sara-{report_id}">{ref_content}</ref>'
    else:
        return ""
