import pytest
from backend.app.services.chunking import chunk_segments
from backend.app.services.extraction import Segment

def test_determinism_and_sections():
    sections=[Segment('# CLI\n'+('show configuration\n'*140),4)]
    one=chunk_segments('doc',sections,350,60)
    two=chunk_segments('doc',sections,350,60)
    assert one==two and len(one)>1
    assert all(c.section=='CLI' and c.page==4 for c in one)
    assert all(c.text.startswith('# CLI') for c in one)
    assert all(len(c.text)<500 for c in one)

def test_duplicate_blocks_and_empty():
    assert chunk_segments('x',[Segment(''),Segment('   ')])==[]
    text='# Heading\nhello'
    assert len(chunk_segments('x',[Segment(text),Segment(text)]))==1

def test_unicode_and_command():
    pieces=chunk_segments('d',[Segment('## Commands\n`````\nshow interfaces terse\n`````\nμ-interface')],200,20)
    assert 'show interfaces terse' in pieces[0].text
    assert 'μ-interface' in pieces[0].text

def test_wrong_overlap():
    with pytest.raises(ValueError):chunk_segments('x',[Segment('ok')],100,100)
