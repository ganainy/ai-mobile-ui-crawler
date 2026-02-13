import pytest
from mobile_crawler.domain.grounding.mapper import LabelMapper
from mobile_crawler.domain.grounding.dtos import OCRResult

def test_mapper_assigns_sequential_labels():
    mapper = LabelMapper()
    results = [
        OCRResult(text="Login", box=(10, 10, 50, 50), confidence=0.9, center=(30, 30)),
        OCRResult(text="Signup", box=(60, 10, 100, 50), confidence=0.8, center=(80, 30)),
    ]
    
    label_map = mapper.assign_labels(results)
    
    assert len(label_map) == 2
    assert 1 in label_map
    assert 2 in label_map
    assert label_map[1] == (30, 30)
    assert label_map[2] == (80, 30)

def test_mapper_clear():
    mapper = LabelMapper()
    results = [OCRResult(text="A", box=(0,0,1,1), confidence=1.0, center=(0,0))]
    mapper.assign_labels(results)
    
    mapper.clear()
    assert len(mapper.get_map()) == 0
