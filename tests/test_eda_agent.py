"""Tests for the EDA agent and its generators.

All LLM calls are mocked so the tests run without an OpenAI API key.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# LLMClient tests
# ---------------------------------------------------------------------------


class TestLLMClient(unittest.TestCase):
    @patch("eda_agent.llm_client.OpenAI")
    def test_chat_returns_content(self, mock_openai_cls):
        """LLMClient.chat should return the content of the first choice."""
        from eda_agent.llm_client import LLMClient

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="module top(); endmodule"))]
        )

        llm = LLMClient(api_key="test-key")
        result = llm.chat(system="sys", user="usr")

        self.assertEqual(result, "module top(); endmodule")
        mock_client.chat.completions.create.assert_called_once()

    @patch("eda_agent.llm_client.OpenAI")
    def test_chat_passes_model_and_temperature(self, mock_openai_cls):
        """LLMClient.chat should forward model name and temperature to the API."""
        from eda_agent.llm_client import LLMClient

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="ok"))]
        )

        llm = LLMClient(model="gpt-3.5-turbo", api_key="k", temperature=0.5)
        llm.chat(system="s", user="u")

        _, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "gpt-3.5-turbo")
        self.assertAlmostEqual(kwargs["temperature"], 0.5)


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


class TestRTLGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.chat.return_value = "module counter(); endmodule"

    def test_generate_returns_llm_output(self):
        from eda_agent.generators.rtl_generator import RTLGenerator

        gen = RTLGenerator(self.mock_llm)
        result = gen.generate("4-bit counter")
        self.assertEqual(result, "module counter(); endmodule")

    def test_generate_calls_llm_with_spec(self):
        from eda_agent.generators.rtl_generator import RTLGenerator

        gen = RTLGenerator(self.mock_llm)
        gen.generate("my spec")
        _, kwargs = self.mock_llm.chat.call_args
        self.assertIn("my spec", kwargs["user"])

    def test_generate_uses_rtl_system_prompt(self):
        from eda_agent.generators.rtl_generator import RTLGenerator
        from eda_agent.prompts.rtl_prompts import RTL_SYSTEM_PROMPT

        gen = RTLGenerator(self.mock_llm)
        gen.generate("spec")
        _, kwargs = self.mock_llm.chat.call_args
        self.assertEqual(kwargs["system"], RTL_SYSTEM_PROMPT)


class TestTestbenchGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.chat.return_value = "module tb_counter(); endmodule"

    def test_generate_returns_llm_output(self):
        from eda_agent.generators.testbench_generator import TestbenchGenerator

        gen = TestbenchGenerator(self.mock_llm)
        result = gen.generate("4-bit counter", "module counter(); endmodule")
        self.assertEqual(result, "module tb_counter(); endmodule")

    def test_generate_includes_rtl_code_in_prompt(self):
        from eda_agent.generators.testbench_generator import TestbenchGenerator

        gen = TestbenchGenerator(self.mock_llm)
        gen.generate("spec", "my rtl code")
        _, kwargs = self.mock_llm.chat.call_args
        self.assertIn("my rtl code", kwargs["user"])

    def test_generate_includes_spec_in_prompt(self):
        from eda_agent.generators.testbench_generator import TestbenchGenerator

        gen = TestbenchGenerator(self.mock_llm)
        gen.generate("my spec", "rtl")
        _, kwargs = self.mock_llm.chat.call_args
        self.assertIn("my spec", kwargs["user"])


class TestSVAGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_llm.chat.return_value = "module counter_sva(); endmodule"

    def test_generate_returns_llm_output(self):
        from eda_agent.generators.sva_generator import SVAGenerator

        gen = SVAGenerator(self.mock_llm)
        result = gen.generate("spec", "rtl")
        self.assertEqual(result, "module counter_sva(); endmodule")

    def test_generate_includes_rtl_and_spec(self):
        from eda_agent.generators.sva_generator import SVAGenerator

        gen = SVAGenerator(self.mock_llm)
        gen.generate("my spec", "my rtl")
        _, kwargs = self.mock_llm.chat.call_args
        self.assertIn("my spec", kwargs["user"])
        self.assertIn("my rtl", kwargs["user"])


# ---------------------------------------------------------------------------
# EDAAgent tests
# ---------------------------------------------------------------------------


class TestEDAAgent(unittest.TestCase):
    def _make_agent(self):
        """Return an EDAAgent with a fully-mocked LLM client."""
        from eda_agent.agent import EDAAgent

        mock_llm = MagicMock()
        responses = iter(
            [
                "module top(); endmodule",          # RTL
                "module tb_top(); endmodule",        # testbench
                "module top_sva(); endmodule",       # SVA
            ]
        )
        mock_llm.chat.side_effect = lambda **_: next(responses)
        agent = EDAAgent(llm_client=mock_llm)
        return agent, mock_llm

    def test_run_returns_eda_result(self):
        from eda_agent.agent import EDAResult

        agent, _ = self._make_agent()
        result = agent.run("4-bit counter", verbose=False)
        self.assertIsInstance(result, EDAResult)

    def test_run_populates_all_fields(self):
        agent, _ = self._make_agent()
        result = agent.run("4-bit counter", verbose=False)
        self.assertEqual(result.specification, "4-bit counter")
        self.assertIn("module top", result.rtl)
        self.assertIn("module tb_top", result.testbench)
        self.assertIn("module top_sva", result.sva)

    def test_run_calls_llm_three_times(self):
        agent, mock_llm = self._make_agent()
        agent.run("spec", verbose=False)
        self.assertEqual(mock_llm.chat.call_count, 3)

    def test_run_verbose_prints_progress(self):
        import io

        agent, _ = self._make_agent()
        with patch("builtins.print") as mock_print:
            agent.run("spec", verbose=True)
        # At least 4 progress messages expected (RTL, TB, SVA, Done)
        self.assertGreaterEqual(mock_print.call_count, 4)

    @patch("eda_agent.agent.LLMClient")
    def test_default_llm_client_created_when_not_supplied(self, mock_llm_cls):
        from eda_agent.agent import EDAAgent

        mock_llm_cls.return_value = MagicMock()
        mock_llm_cls.return_value.chat.return_value = "x"
        EDAAgent(model="gpt-3.5-turbo")
        mock_llm_cls.assert_called_once_with(model="gpt-3.5-turbo")


# ---------------------------------------------------------------------------
# File utilities tests
# ---------------------------------------------------------------------------


class TestSaveResults(unittest.TestCase):
    def _make_result(self):
        from eda_agent.agent import EDAResult

        return EDAResult(
            specification="spec",
            rtl="module rtl(); endmodule",
            testbench="module tb(); endmodule",
            sva="module sva(); endmodule",
        )

    def test_files_are_created(self):
        from eda_agent.utils.file_utils import save_results

        with TemporaryDirectory() as tmp:
            paths = save_results(self._make_result(), output_dir=tmp)
        # All three paths must have existed in the temp dir (they were returned)
        self.assertIn("rtl", paths)
        self.assertIn("testbench", paths)
        self.assertIn("sva", paths)

    def test_file_contents_match(self):
        from eda_agent.utils.file_utils import save_results

        result = self._make_result()
        with TemporaryDirectory() as tmp:
            paths = save_results(result, output_dir=tmp)
            self.assertEqual(Path(paths["rtl"]).read_text(), result.rtl)
            self.assertEqual(Path(paths["testbench"]).read_text(), result.testbench)
            self.assertEqual(Path(paths["sva"]).read_text(), result.sva)

    def test_output_directory_is_created(self):
        from eda_agent.utils.file_utils import save_results

        with TemporaryDirectory() as tmp:
            new_dir = Path(tmp) / "nested" / "output"
            save_results(self._make_result(), output_dir=str(new_dir))
            self.assertTrue(new_dir.is_dir())


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI(unittest.TestCase):
    @patch("main.EDAAgent")
    @patch("main.save_results")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_main_with_spec_flag(self, mock_save, mock_agent_cls):
        from main import main

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.run.return_value = MagicMock()
        mock_save.return_value = {"rtl": Path("/tmp/design.sv")}

        rc = main(["--spec", "4-bit counter"])
        self.assertEqual(rc, 0)
        mock_agent.run.assert_called_once()

    @patch("main.EDAAgent")
    @patch("main.save_results")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_main_with_spec_file(self, mock_save, mock_agent_cls):
        from main import main

        with TemporaryDirectory() as tmp:
            spec_file = Path(tmp) / "spec.txt"
            spec_file.write_text("4-bit counter")

            mock_agent = MagicMock()
            mock_agent_cls.return_value = mock_agent
            mock_agent.run.return_value = MagicMock()
            mock_save.return_value = {"rtl": Path("/tmp/design.sv")}

            rc = main(["--spec-file", str(spec_file)])
        self.assertEqual(rc, 0)

    @patch.dict("os.environ", {}, clear=True)
    def test_main_missing_api_key_returns_error(self):
        from main import main

        rc = main(["--spec", "counter"])
        self.assertEqual(rc, 1)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "k"})
    def test_main_missing_spec_file_returns_error(self):
        from main import main

        rc = main(["--spec-file", "/nonexistent/path/spec.txt"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
