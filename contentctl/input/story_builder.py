import re
import sys
import pathlib
from pydantic import ValidationError

from contentctl.objects.story import Story
from contentctl.objects.config import Config
from contentctl.input.yml_reader import YmlReader


class StoryBuilder():
    story: Story

    def setObject(self, path: pathlib.Path) -> None:
        yml_dict = YmlReader.load_file(path)

        try:
            self.story = Story.model_validate(yml_dict)
        except ValidationError as e:
            print('Validation Error for file ' + str(path))
            print(e)
            sys.exit(1)

    def reset(self) -> None:
        self.story = None

    def getObject(self) -> Story:
        return self.story

    def addDetections(self, detections: list, config: Config) -> None:
        matched_detection_names = []
        matched_detections = []
        mitre_attack_enrichments = []
        mitre_attack_tactics = set()
        datamodels = set()
        kill_chain_phases = set()

        for detection in detections:
            if detection:
                for detection_analytic_story in detection.tags.analytic_story:
                    if detection_analytic_story == self.story.name:
                        matched_detection_names.append(str(f'{config.build.prefix} - ' + detection.name + ' - Rule'))
                        mitre_attack_enrichments_list = []
                        if (detection.tags.mitre_attack_enrichments):
                            for attack in detection.tags.mitre_attack_enrichments:
                                mitre_attack_enrichments_list.append({"mitre_attack_technique": attack.mitre_attack_technique})
                        tags_obj = {"mitre_attack_enrichments": mitre_attack_enrichments_list}
                        matched_detections.append({
                            "name": detection.name,
                            "source": detection.getSource(),
                            "type": detection.type,
                            "tags": tags_obj
                        })
                        datamodels.update(detection.datamodel)
                        if detection.tags.kill_chain_phases:
                            kill_chain_phases.update(detection.tags.kill_chain_phases)

                        if detection.tags.mitre_attack_enrichments:
                            for attack_enrichment in detection.tags.mitre_attack_enrichments:
                                mitre_attack_tactics.update(attack_enrichment.mitre_attack_tactics)
                                if attack_enrichment.mitre_attack_id not in [attack.mitre_attack_id for attack in mitre_attack_enrichments]:
                                    mitre_attack_enrichments.append(attack_enrichment)

        self.story.detections = matched_detections
        self.story.tags.datamodels = sorted(list(datamodels))
        self.story.tags.kill_chain_phases = sorted(list(kill_chain_phases))
        self.story.tags.mitre_attack_enrichments = mitre_attack_enrichments
        self.story.tags.mitre_attack_tactics = sorted(list(mitre_attack_tactics))


    def addBaselines(self, baselines: list) -> None:
        matched_baseline_names = []
        for baseline in baselines:
            for baseline_analytic_story in  baseline.tags.analytic_story:
                if baseline_analytic_story == self.story.name:
                    matched_baseline_names.append(str(f'ESCU - ' + baseline.name))

        self.story.baseline_names = matched_baseline_names

    def addInvestigations(self, investigations: list) -> None:
        matched_investigation_names = []
        matched_investigations = []
        for investigation in investigations:
            for investigation_analytic_story in  investigation.tags.analytic_story:
                if investigation_analytic_story == self.story.name:
                    matched_investigations.append(investigation)

        self.story.investigations = matched_investigations

    def addAuthorCompanyName(self) -> None:
        match_author = re.search(r'^([^,]+)', self.story.author)
        if match_author is None:
            self.story.author = 'no'
        else:
            self.story.author = match_author.group(1)

        match_company = re.search(r',\s?(.*)$', self.story.author)
        if match_company is None:
            self.story.author_company = 'no'
        else:
            self.story.author_company = match_company.group(1)
