from stockhaiku.rendering import CollageGenerator


def test_generate_tree():
    images = {
        1: (100, 50),
        2: (50, 100),
        3: (300, 400),
    }
    fitter = CollageGenerator(images)
    root = fitter.generate_tree('hv')
    print(root)
    assert root.width == 460

def test_walk_images():
    images = {
        1: (100, 50),
        2: (50, 100),
        3: (300, 400),
    }
    fitter = CollageGenerator(images)
    root = fitter.generate_tree('hv')
    images = list(root.walk_images())
    print(images)
    assert False