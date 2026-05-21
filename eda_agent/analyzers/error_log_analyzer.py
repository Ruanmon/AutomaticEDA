"""EDA simulation error-log analyzer.

Usage examples::

    # Analyze an error log against RTL files in a directory
    python main.py --analyze-error "ERROR: ..." --rtl-dir ./output

    # Read the error log from a file
    python main.py --analyze-error-file sim.log --rtl-dir ./output
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..llm_client import LLMClient
from ..prompts.error_log_prompts import ERROR_LOG_SYSTEM_PROMPT, ERROR_LOG_USER_PROMPT
from ..utils.rtl_searcher import format_rtl_context


@dataclass
class ErrorAnalysisResult:
    """Container for the output of :class:`ErrorLogAnalyzer`.

    Attributes
    ----------
    error_log:
        The original error log provided by the user.
    rtl_files:
        The RTL source files used as context during analysis.
    analysis:
        The LLM's analysis: error summary, root causes, and suggested fixes.
    """

    error_log: str
    rtl_files: dict[str, str] = field(default_factory=dict)
    analysis: str = ""


class ErrorLogAnalyzer:
    """Analyzes EDA simulation error logs against RTL source files.

    The analyzer sends the error log together with the contents of the
    provided RTL files to the LLM and returns a structured analysis that
    includes root-cause identification and suggested fixes.

    Parameters
    ----------
    llm_client:
        A pre-configured :class:`~eda_agent.llm_client.LLMClient`.  When
        *None* (default) a new client is created from the remaining keyword
        arguments.
    model:
        Model name forwarded to :class:`~eda_agent.llm_client.LLMClient` when
        *llm_client* is not supplied (default: ``"gpt-4o"``).
    **kwargs:
        Additional keyword arguments forwarded to
        :class:`~eda_agent.llm_client.LLMClient`.

    Examples
    --------
    >>> from eda_agent.analyzers import ErrorLogAnalyzer
    >>> from eda_agent.utils.rtl_searcher import collect_rtl_files
    >>>
    >>> analyzer = ErrorLogAnalyzer()
    >>> rtl_files = collect_rtl_files("./output")
    >>> result = analyzer.analyze(error_log="...", rtl_files=rtl_files)
    >>> print(result.analysis)
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        model: str = "gpt-4o",
        **kwargs,
    ) -> None:
        if llm_client is None:
            llm_client = LLMClient(model=model, **kwargs)
        self.llm_client = llm_client

    def analyze(self, error_log: str, rtl_files: dict[str, str]) -> ErrorAnalysisResult:
        """Analyze *error_log* in the context of *rtl_files*.

        Parameters
        ----------
        error_log:
            The raw error/warning text produced by an EDA simulation tool.
        rtl_files:
            A mapping of ``filename → source_content`` for all RTL files that
            should be considered during analysis.  Obtain this mapping with
            :func:`~eda_agent.utils.rtl_searcher.collect_rtl_files`.

        Returns
        -------
        ErrorAnalysisResult
            A dataclass containing the original inputs and the LLM's analysis.
        """
        rtl_context_str = format_rtl_context(rtl_files)
        user_prompt = ERROR_LOG_USER_PROMPT.format(
            error_log=error_log,
            rtl_context=rtl_context_str,
        )
        analysis = self.llm_client.chat(
            system=ERROR_LOG_SYSTEM_PROMPT,
            user=user_prompt,
        )
        return ErrorAnalysisResult(
            error_log=error_log,
            rtl_files=rtl_files,
            analysis=analysis,
        )

