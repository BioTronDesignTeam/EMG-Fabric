import sys
from pathlib import Path

EMG2POSE_ROOT = Path(__file__).resolve().parent / "emg2pose_main"
sys.path.insert(0, str(EMG2POSE_ROOT))

from .emg2pose_main.emg2pose.lightning import Emg2PoseModule
from .emg2pose_main.emg2pose.utils import generate_hydra_config_from_overrides
from .emg2pose_main.emg2pose.lightning import Emg2PoseModule
import torch

class VEMG2POSEInference():
    def __init__(self):
        self.model = None
        self.checkpoint = None
        self.module = None 

    def load_model(self,model,checkpoint):
        if model == self.model or checkpoint == self.checkpoint:
            return
        config = generate_hydra_config_from_overrides(
            overrides=[
                f"experiment={model}",
                f"checkpoint={checkpoint}"
            ]
        )
        device = torch.device("cpu")

        if self.module == None:
            self.module = Emg2PoseModule.load_from_checkpoint(
                config.checkpoint,
                network=config.network,
                weights_only=False
            )
        else:
            self.module.network = config.network
            checkpoint = torch.load(checkpoint, map_location=device,weights_only=False)
            self.module.load_state_dict(checkpoint["state_dict"])
        self.module.to(device)
        self.module.eval()

        self.model = model
        self.checkpoint = checkpoint

    def reset(self):
        self.elapsed_steps = 0
        self.previous_pose = None

    def predict(self, emg):
        preds = self.module.model._predict_pose(
            emg,
            initial_pos=self.previous_pose,
            start_step=self.elapsed_steps,
        )

        self.previous_pose = preds[:, :, -1]
        self.elapsed_steps += preds.shape[-1]

        return preds