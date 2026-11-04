from green.models import EventSeries
from green.simulator import generate_events


def events_for(series: EventSeries):
    return tuple(event for event in generate_events() if event.series is series)


def metadata(event) -> dict[str, str]:
    return dict(event.metadata)