"""Stack Cost"""
from src.character.skills.costs.base import SkillCost

class StackCost(SkillCost):
    """스택 비용"""
    def __init__(self, field: str, amount: int):
        super().__init__("stack")
        self.field = field
        self.amount = amount
    
    def can_afford(self, user, context):
        if not hasattr(user, self.field):
            return False, f"기믹 필드 없음: {self.field}"
        current = getattr(user, self.field, 0)
        if current >= self.amount:
            return True, ""
        return False, f"{self.field} 부족 ({current}/{self.amount})"
    
    def consume(self, user, context):
        if not hasattr(user, self.field):
            return False
        current = getattr(user, self.field, 0)
        if current < self.amount:
            return False
        setattr(user, self.field, current - self.amount)
        return True
    
    def get_description(self, user):
        # 필드명을 한글로 변환
        field_names = {
            "dragon_power": "용력",
            "dragon_marks": "용표",
            "nature_points": "자연 포인트",
            "rage_stacks": "분노",
            "venom_power": "독",
            "shadow_count": "그림자",
            "sword_aura": "검기",
            "melody_stacks": "멜로디",
            "heat": "열",
            "will_gauge": "의지",
            "holy_gauge": "신성력",
            "divinity": "신성력",
            "magazine": "탄창",
            "program_virus": "바이러스",
            "program_firewall": "방화벽",
            "program_encryption": "암호화",
            "program_backup": "백업",
            "program_ai": "AI",
            "program_quantum": "양자",
            "program_neural": "신경망",
            "program_blockchain": "블록체인",
            "program_cloud": "클라우드",
            "program_edge": "엣지",
            "program_iot": "IoT",
            "program_5g": "5G",
            "program_ar": "AR",
            "program_vr": "VR",
            "program_ml": "ML",
            "program_dl": "DL",
            "program_nlp": "NLP",
            "program_cv": "CV",
            "program_rl": "RL",
            "program_gan": "GAN",
            "program_cnn": "CNN",
            "program_rnn": "RNN",
            "program_lstm": "LSTM",
            "program_transformer": "트랜스포머",
            "program_bert": "BERT",
            "program_gpt": "GPT",
            "program_resnet": "ResNet",
            "program_vgg": "VGG",
            "program_inception": "Inception",
            "program_mobilenet": "MobileNet",
            "program_efficientnet": "EfficientNet",
            "program_yolo": "YOLO",
            "program_ssd": "SSD",
            "program_rcnn": "R-CNN",
            "program_faster_rcnn": "Faster R-CNN",
            "program_mask_rcnn": "Mask R-CNN",
            "program_retinanet": "RetinaNet",
            "program_fpn": "FPN",
            "program_densenet": "DenseNet",
            "program_squeezenet": "SqueezeNet",
            "program_shufflenet": "ShuffleNet",
            "program_mnasnet": "MnasNet",
            "program_efficientdet": "EfficientDet",
            "program_centernet": "CenterNet",
            "program_cornernet": "CornerNet",
            "program_fcos": "FCOS",
            "program_atss": "ATSS",
            "program_paa": "PAA",
            "program_detr": "DETR",
            "program_deformable_detr": "Deformable DETR",
            "program_sparse_rcnn": "Sparse R-CNN",
            "program_dab_detr": "DAB-DETR",
            "program_dn_detr": "DN-DETR",
            "program_dino": "DINO",
            "program_rt_detr": "RT-DETR",
            "program_yolov8": "YOLOv8",
            "program_yolov9": "YOLOv9",
            "program_yolov10": "YOLOv10",
            "program_yolox": "YOLOX",
            "program_yolov7": "YOLOv7",
            "program_yolov6": "YOLOv6",
            "program_yolov5": "YOLOv5",
            "program_yolov4": "YOLOv4",
            "program_yolov3": "YOLOv3",
            "program_yolov2": "YOLOv2",
            "program_yolov1": "YOLOv1",
            "program_ssd300": "SSD300",
            "program_ssd512": "SSD512",
            "program_ssdlite": "SSDLite",
            "program_mobilenet_ssd": "MobileNet-SSD",
            "program_peleenet_ssd": "PeleeNet-SSD",
            "program_rfb_net": "RFB-Net",
            "program_m2det": "M2Det",
            "program_refinedet": "RefineDet",
            "program_fssd": "FSSD",
            "program_dssd": "DSSD",
            "program_dsod": "DSOD",
            "program_stssd": "STSSD",
            "program_ron": "RON",
            "program_stdn": "STDN",
            "program_retinanet": "RetinaNet",
            "program_focal_loss": "Focal Loss",
            "program_ghost_net": "GhostNet",
            "program_mobilenet_v3": "MobileNetV3",
            "program_efficientnet_v2": "EfficientNetV2",
            "program_regnet": "RegNet",
            "program_vision_transformer": "Vision Transformer",
            "program_swin_transformer": "Swin Transformer",
            "program_deit": "DeiT",
            "program_cvt": "CvT",
            "program_pit": "PiT",
            "program_t2t_vit": "T2T-ViT",
            "program_cait": "CaiT",
            "program_crossvit": "CrossViT",
            "program_twins": "Twins",
            "program_pvt": "PVT",
            "program_coatnet": "CoAtNet",
            "program_convit": "ConViT",
            "program_levit": "LeViT",
            "program_esvit": "EsViT",
            "program_swin_v2": "SwinV2",
            "program_maxvit": "MaxViT",
            "program_convnext": "ConvNeXt",
            "program_repvit": "RepViT",
            "program_efficientvit": "EfficientViT",
            "program_mobilevit": "MobileViT",
            "program_mobilevit_v2": "MobileViTV2",
            "program_edgevit": "EdgeViT",
            "program_tinyvit": "TinyViT",
            "program_fastvit": "FastViT",
            "program_fastervit": "FasterViT",
            "program_streamvit": "StreamViT",
            "program_lightvit": "LightViT",
            "program_compactvit": "CompactViT",
            "program_smallvit": "SmallViT",
            "program_minivit": "MiniViT",
            "program_nanovit": "NanoViT",
            "program_picovit": "PicoViT",
            "program_femtovit": "FemtoViT",
            "program_attovit": "AttoViT",
            "program_zeptovit": "ZeptoViT",
            "program_yoctovit": "YoctoViT",
            "program_planckvit": "PlanckViT",
        }
        field_name = field_names.get(self.field, self.field)
        return f"{field_name} {self.amount}"
