"""Storage failures exposed to pipeline/API boundaries without authorizing a purchase."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session


class PersistenceError(Exception):
    """A database operation could not be completed."""


class RecordNotFound(PersistenceError):
    """The requested record does not exist."""


class DuplicateRecord(PersistenceError):
    """The operation would duplicate an existing identity."""


class InvalidTransition(PersistenceError):
    """The requested lifecycle transition is not permitted."""


class InvalidEvidence(PersistenceError):
    """The supplied evidence violates a persistence invariant."""


class DatabaseBusyError(PersistenceError):
    """A writer could not obtain the database lock within its bounded wait."""


@contextmanager
def storage_errors() -> Iterator[None]:
    """Translate expected SQL errors while retaining the original cause."""
    try:
        yield
    except IntegrityError as error:
        message = str(error.orig).lower()
        if "unique constraint" in message or "duplicate key" in message:
            raise DuplicateRecord("An identity already exists") from error
        raise InvalidEvidence("A database integrity constraint rejected this write") from error
    except OperationalError as error:
        if "locked" in str(error.orig).lower() or "busy" in str(error.orig).lower():
            raise DatabaseBusyError("Database writer lock timed out") from error
        raise PersistenceError("Database operation failed") from error


def flush(session: Session) -> None:
    """Flush without committing; the transaction owner controls rollback."""
    with storage_errors():
        session.flush()
