from __future__ import annotations


def test_run_in_worker_thread_returns_value():
    from features.image_generation.midjourney_runner import _run_in_worker_thread

    assert _run_in_worker_thread("unit", lambda: 123) == 123


def test_run_in_worker_thread_propagates_exception():
    from features.image_generation.midjourney_runner import _run_in_worker_thread

    class Boom(Exception):
        pass

    def _fn():
        raise Boom("nope")

    try:
        _run_in_worker_thread("unit", _fn)
        assert False, "expected exception"
    except Boom as e:
        assert "nope" in str(e)


def test_web_controller_close_does_not_close_cdp_browser():
    from integrations.midjourney.automation.midjourney_web_controller import MidjourneyWebController

    ctrl = MidjourneyWebController(dry_run=True)

    class DummyPage:
        closed = False

        def close(self):
            self.closed = True

    class DummyBrowser:
        def close(self):
            raise AssertionError("browser.close should not be called for CDP connections")

    ctrl.page = DummyPage()
    ctrl.browser = DummyBrowser()
    ctrl.playwright = object()  # should be ignored in dry_run close path, but kept non-None for coverage
    ctrl._connected_over_cdp = True

    # close should swallow errors, close the page, and not close browser
    ctrl.close()
    assert ctrl.page is None

