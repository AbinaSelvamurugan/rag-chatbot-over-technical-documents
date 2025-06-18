from io import BytesIO
import pytest
from backend.app.services.extraction import extract,ExtractionError

@pytest.mark.parametrize('name,body',[
  ('readme.md',b'# Section\n\nConfigure `set system host-name lab`'),
  ('notes.txt',b'hello\nshow interfaces terse'),
  ('guide.html',b'<html><body><nav>IGNORE NAV</nav><main><h2>CLI</h2><pre>show configuration</pre><table><tr><td>name</td><td>value</td></tr></table></main></body></html>')
])
def test_extract(name,body):
    segment=extract(name,body)[0]
    assert segment.text
    assert 'IGNORE NAV' not in segment.text

def test_pdf_valid():
    from reportlab.pdfgen.canvas import Canvas
    buffer=BytesIO(); canvas=Canvas(buffer)
    canvas.drawString(50,700,'CLI mode: operational')
    canvas.showPage();canvas.drawString(50,700,'Page two: configuration')
    canvas.save()
    segments=extract('paper.pdf',buffer.getvalue())
    assert [s.page_number for s in segments]==[1,2]
    assert 'operational' in segments[0].text

@pytest.mark.parametrize('filename,data', [('bad.pdf',b'malformed'),('bad.md',b'\x00'),('empty.txt',b''),('bad.zip',b'stuff'),('latin.md',b'\xff')])
def test_reject_invalid(filename,data):
    with pytest.raises(ExtractionError):extract(filename,data)

def test_unicode():
    assert 'μ' in extract('utf8.md','# Signals\nμs latency'.encode())[0].text
