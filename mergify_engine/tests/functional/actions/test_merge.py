# -*- encoding: utf-8 -*-
#
# Copyright © 2018 Mehdi Abaakouk <sileht@sileht.net>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import logging

import yaml

from mergify_engine import config
from mergify_engine import constants
from mergify_engine import context
from mergify_engine.tests.functional import base


LOG = logging.getLogger(__name__)


class TestMergeAction(base.FunctionalTestBase):
    SUBSCRIPTION_ACTIVE = True

    async def test_merge_draft(self):
        rules = {
            "pull_request_rules": [
                {
                    "name": "Merge",
                    "conditions": [
                        f"base={self.main_branch_name}",
                        "label=automerge",
                    ],
                    "actions": {"merge": {}},
                },
            ]
        }

        await self.setup_repo(yaml.dump(rules))

        p, _ = await self.create_pr(draft=True)
        await self.add_label(p["number"], "automerge")
        await self.run_engine()

        ctxt = await context.Context.create(self.repository_ctxt, p, [])
        checks = await ctxt.pull_engine_check_runs
        assert len(checks) == 2
        check = checks[1]
        assert check["conclusion"] is None
        assert check["output"]["title"] == "Draft flag needs to be removed"
        assert check["output"]["summary"] == ""

        await self.remove_label(p["number"], "automerge")
        await self.run_engine()
        ctxt = await context.Context.create(self.repository_ctxt, p, [])
        checks = await ctxt.pull_engine_check_runs
        assert len(checks) == 2
        check = checks[1]
        assert check["conclusion"] == "cancelled"
        assert check["output"]["title"] == "The rule doesn't match anymore"

    async def test_merge_with_installation_token(self):
        rules = {
            "pull_request_rules": [
                {
                    "name": "merge on main",
                    "conditions": [f"base={self.main_branch_name}"],
                    "actions": {"merge": {}},
                },
            ]
        }

        await self.setup_repo(yaml.dump(rules))

        p, _ = await self.create_pr()
        await self.run_engine()
        await self.wait_for("pull_request", {"action": "closed"})

        p = await self.get_pull(p["number"])
        self.assertEqual(True, p["merged"])
        self.assertEqual(config.BOT_USER_LOGIN, p["merged_by"]["login"])

    async def test_merge_with_oauth_token(self):
        rules = {
            "pull_request_rules": [
                {
                    "name": "merge on main",
                    "conditions": [f"base={self.main_branch_name}"],
                    "actions": {"merge": {"merge_bot_account": "{{ body }}"}},
                },
            ]
        }

        await self.setup_repo(yaml.dump(rules))

        p, _ = await self.create_pr(message="mergify-test4")
        await self.run_engine()
        await self.wait_for("pull_request", {"action": "closed"})

        p = await self.get_pull(p["number"])
        self.assertEqual(True, p["merged"])
        self.assertEqual("mergify-test4", p["merged_by"]["login"])

    async def test_merge_branch_protection_linear_history(self):
        rules = {
            "pull_request_rules": [
                {
                    "name": "merge",
                    "conditions": [f"base={self.main_branch_name}"],
                    "actions": {"merge": {}},
                }
            ]
        }

        await self.setup_repo(yaml.dump(rules))

        protection = {
            "required_status_checks": None,
            "required_linear_history": True,
            "required_pull_request_reviews": None,
            "restrictions": None,
            "enforce_admins": False,
        }

        await self.branch_protection_protect(self.main_branch_name, protection)

        p1, _ = await self.create_pr()
        await self.run_engine()
        await self.wait_for("check_run", {"check_run": {"conclusion": "failure"}})

        ctxt = await context.Context.create(self.repository_ctxt, p1, [])
        checks = [
            c
            for c in await ctxt.pull_engine_check_runs
            if c["name"] == "Rule: merge (merge)"
        ]
        assert "failure" == checks[0]["conclusion"]
        assert (
            "Branch protection setting 'linear history' conflicts with Mergify configuration"
            == checks[0]["output"]["title"]
        )

    async def test_merge_template(self):
        rules = {
            "pull_request_rules": [
                {
                    "name": "merge on main",
                    "conditions": [f"base={self.main_branch_name}"],
                    "actions": {
                        "merge": {
                            "commit_message_template": """{{ title }} (#{{ number }})
{{body}}
superRP!
""",
                        }
                    },
                },
            ]
        }
        await self.setup_repo(yaml.dump(rules))

        p, _ = await self.create_pr(message="mergify-test4")
        await self.run_engine()
        await self.wait_for("pull_request", {"action": "closed"})

        p2 = await self.get_pull(p["number"])
        self.assertEqual(True, p2["merged"])
        p3 = await self.get_commit(p2["merge_commit_sha"])
        assert (
            f"""test_merge_template: pull request n1 from fork (#{p2['number']})

mergify-test4
superRP!"""
            == p3["commit"]["message"]
        )
        ctxt = await context.Context.create(self.repository_ctxt, p, [])
        summary = await ctxt.get_engine_check_run(constants.SUMMARY_NAME)
        assert (
            """
:bangbang: **Action Required** :bangbang:

> **The configuration uses the deprecated `commit_message` mode of the merge action.**
> A brownout is planned for the whole March 21th, 2022 day.
> This option will be removed on April 25th, 2022.
> For more information: https://docs.mergify.com/actions/merge/

"""
            not in summary["output"]["summary"]
        )
