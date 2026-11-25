import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtQuickControls2 import QQuickStyle

from .core.bus import SignalBus
from .signals.synthetic import SyntheticSource
from .ui.bridge import WorkspaceBridge
from .ui.signal_plot import SignalPlot
from .phantom.controller import PhantomController
from .robot.controller import HandController
from .ml.controller import MLController


def main():
    QQuickStyle.setStyle('Fusion')
    app = QGuiApplication(sys.argv)
    app.setApplicationName('EMG Fabric Workstation')
    bus = SignalBus()
    source = SyntheticSource(bus)
    SignalPlot.bus = bus
    HandController.bus = bus
    qmlRegisterType(SignalPlot, 'Workstation', 1, 0, 'SignalPlot')
    hand = HandController()
    bridge = WorkspaceBridge(source, hand)
    phantom = PhantomController(source)
    ml = MLController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('workspace', bridge)
    engine.rootContext().setContextProperty('phantom', phantom)
    engine.rootContext().setContextProperty('hand', hand)
    engine.rootContext().setContextProperty('ml', ml)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'ui/qml/Main.qml')))
    if not engine.rootObjects():
        phantom.close()
        hand.close()
        return 1
    source.start()
    app.aboutToQuit.connect(source.close)
    app.aboutToQuit.connect(phantom.close)
    app.aboutToQuit.connect(hand.close)
    app.aboutToQuit.connect(ml.close)
    return app.exec()
