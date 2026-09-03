from app.services.job_extractor import parse_job_html


def test_json_ld_job_posting_is_preferred():
    html = """
    <html><head>
      <meta property="og:site_name" content="Fallback Company">
      <script type="application/ld+json">
      {"@context":"https://schema.org","@type":"JobPosting",
       "title":"FPGA Design Engineer","hiringOrganization":{"name":"GE Example"},
       "jobLocation":{"address":{"addressLocality":"Berlin","addressCountry":"DE"}},
       "employmentType":"FULL_TIME"}
      </script>
    </head></html>
    """
    result = parse_job_html("https://careers.example/jobs/1", html)
    assert result.company == "GE Example"
    assert result.role == "FPGA Design Engineer"
    assert result.location == "Berlin, DE"
    assert result.employment_type == "FULL_TIME"


def test_apply_link_is_discovered():
    result = parse_job_html(
        "https://jobs.example/role",
        '<html><head><meta property="og:title" content="Engineer"></head><body><a href="/apply/42">Apply now</a></body></html>',
    )
    assert result.application_url == "https://jobs.example/apply/42"
