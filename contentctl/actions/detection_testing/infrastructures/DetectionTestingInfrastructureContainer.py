from contentctl.actions.detection_testing.infrastructures.DetectionTestingInfrastructure import (
    DetectionTestingInfrastructure,
)
import docker.models.resource
import docker.models.containers
import docker
import docker.types
from contentctl.objects.test_config import (
    CONTAINER_APP_DIR,
    LOCAL_APP_DIR,
)


class DetectionTestingInfrastructureContainer(DetectionTestingInfrastructure):
    container: docker.models.resource.Model = None

    def start(self):
        self.container = self.make_container()
        self.container.start()

    def finish(self):
        if self.container is not None:
            try:
                self.removeContainer()
                pass
            except Exception as e:
                raise (Exception(f"Error removing container: {str(e)}"))
        super().finish()

    def get_name(self) -> str:
        return self.infrastructure.instance_name

    def get_docker_client(self):
        try:
            c = docker.client.from_env()

            return c
        except Exception as e:
            raise (Exception(f"Failed to get docker client: {str(e)}"))

    def check_for_teardown(self):

        try:
            self.get_docker_client().containers.get(self.get_name())
        except Exception as e:
            if self.sync_obj.terminate is not True:
                self.pbar.write(
                    f"Error: could not get container [{self.get_name()}]: {str(e)}"
                )
                self.sync_obj.terminate = True

        if self.sync_obj.terminate:
            self.finish()

        super().check_for_teardown()

    def make_container(self) -> docker.models.resource.Model:
        # First, make sure that the container has been removed if it already existed
        self.removeContainer()

        ports_dict = {
            "8000/tcp": self.infrastructure.web_ui_port,
            "8088/tcp": self.infrastructure.hec_port,
            "8089/tcp": self.infrastructure.api_port,
        }

        mounts = [
            docker.types.Mount(
                source=str(LOCAL_APP_DIR.absolute()),
                target=str(CONTAINER_APP_DIR.absolute()),
                type="bind",
                read_only=True,
            )
        ]

        environment = {}
        environment["SPLUNK_START_ARGS"] = "--accept-license"
        environment["SPLUNK_PASSWORD"] = self.infrastructure.splunk_app_password
        environment["SPLUNK_APPS_URL"] = ",".join(
            str(p.hardcoded_path) for p in self.global_config.apps 
        )
        if (
            self.global_config.splunkbase_password is not None
            and self.global_config.splunkbase_username is not None
        ):
            environment["SPLUNKBASE_USERNAME"] = self.global_config.splunkbase_username
            environment["SPLUNKBASE_PASSWORD"] = self.global_config.splunkbase_password


        def emit_docker_run_equivalent():
            environment_string = " ".join([f'-e "{k}={environment.get(k)}"' for k in environment.keys()])
            print(f"docker run -d "\
                  f"-p {self.infrastructure.web_ui_port}:8000 "
                  f"-p {self.infrastructure.hec_port}:8088 "
                  f"-p {self.infrastructure.api_port}:8089 "
                  f"{environment_string} "            
                  f" --name {self.get_name()} "
                  f"--platform linux/amd64"
                  f"{self.global_config.infrastructure_config.full_image_path}")
        emit_docker_run_equivalent()
        import sys
        sys.exit(1)
        container = self.get_docker_client().containers.create(
            self.global_config.infrastructure_config.full_image_path,
            ports=ports_dict,
            environment=environment,
            name=self.get_name(),
            mounts=mounts,
            detach=True,
            platform="linux/amd64"
        )

        return container

    def removeContainer(self, removeVolumes: bool = True, forceRemove: bool = True):
        try:
            container: docker.models.containers.Container = (
                self.get_docker_client().containers.get(self.get_name())
            )
        except Exception as e:
            # Container does not exist, no need to try and remove it
            return
        try:

            # container was found, so now we try to remove it
            # v also removes volumes linked to the container
            container.remove(v=removeVolumes, force=forceRemove)
            # remove it even if it is running. remove volumes as well
            # No need to print that the container has been removed, it is expected behavior

        except Exception as e:
            raise (
                Exception(
                    f"Could not remove Docker Container [{self.get_name()}]: {str(e)}"
                )
            )
