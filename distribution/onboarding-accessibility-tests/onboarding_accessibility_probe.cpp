// SPDX-License-Identifier: GPL-3.0-only
// Production providers, controller, navigation, Page/Dialog/FlatButton QML.
// Only external settings/interactive services and rendering/styling are substitutes.
#include <QAccessible>
#include <QElapsedTimer>
#include <QFontDatabase>
#include <QGuiApplication>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickView>
#include <QRawFont>
#include <QThread>
#include <QDebug>
#include <QtQuick/private/qaccessiblequickview_p.h>
#include <QtQuick/private/qaccessiblequickitem_p.h>
#include <QtQuick/private/qquickitem_p.h>
#include <cstdio>
#include <memory>
#include "logger.h"
#include "accessibility/internal/accessibilitycontroller.h"
#include "accessibility/internal/accessibleapprootobject.h"
#include "accessibility/internal/accessiblewindowinterface.h"
#include "accessibility/internal/accessibleobject.h"
#include "accessibility/internal/accessiblestub.h"
#include "accessibility/internal/qaccessibleinterfaceregister.h"
#include "ui/internal/navigationcontroller.h"
#include "ui/qml/Muse/Ui/qmlaccessible.h"
#include "ui/qml/Muse/Ui/navigationsection.h"
#include "ui/qml/Muse/Ui/navigationpanel.h"
#include "ui/qml/Muse/Ui/navigationcontrol.h"
#include "rcommand/internal/commanddispatcher.h"
#include "actions/internal/actionsdispatcher.h"
#include "ui/navigationcommands.h"
#include "async/processevents.h"
#include "src/appshell/internal/dialogaccessibility.h"
#include "src/appshell/qml/Audacity/AppShell/FirstLaunchSetup/firstlaunchsetupmodel.h"
#include "src/appshell/tests/mocks/appshellconfigurationmock.h"
#include "interactive/tests/mocks/interactivemock.h"

using namespace muse;
using namespace muse::accessibility;
// Muse installs its own Qt message handler. Its normal Windows console sink
// uses OutputDebugString even with QT_FORCE_STDERR_LOGGING, so the fixture must
// retain messages in the parent's captured pipe after that handover as well.
class ProbeStderrLogDest final : public kors::logger::LogDest
{
public:
    ProbeStderrLogDest() : LogDest(kors::logger::LogLayout("${message}")) {}
    std::string name() const override { return "OnboardingProbeStderr"; }
    void write(const kors::logger::LogMsg& message) override
    {
        const auto output = m_layout.output(message);
        std::fwrite(output.data(), 1, output.size(), stderr);
        std::fputc('\n', stderr);
        std::fflush(stderr);
    }
};
static QAccessibleInterfaceRegister registry;
// The same getter-then-stub dispatch used by AccessibilityModule's factory.
static QAccessibleInterface* factory(const QString& name, QObject* object)
{
    if (auto getter = registry.interfaceGetter(name)) return getter(object);
    return AccessibleStub::accessibleInterface(object);
}
// Reinstall the stock Qt interface constructors after Muse registration to
// exercise factory precedence independently of this host's plugin load order.
static QAccessibleInterface* stockQuickFactory(const QString& name, QObject* object)
{
    if (name == "QQuickWindow") return new QAccessibleQuickWindow(qobject_cast<QQuickWindow*>(object));
    if (name == "QQuickItem") {
        auto item = qobject_cast<QQuickItem*>(object);
        if (QQuickItemPrivate::get(item)->isAccessible) return new QAccessibleQuickItem(item);
    }
    return nullptr;
}
static void require(bool condition, const char* message)
{
    if (!condition) { qCritical().noquote() << "FAIL:" << message; std::exit(1); }
}

static bool waitUntil(const std::function<bool()>& condition);
#include "accessibility_graph_tests.h"

static void process()
{
    async::processMessages();
    QCoreApplication::processEvents();
}
static bool waitUntil(const std::function<bool()>& condition)
{
    QElapsedTimer timer; timer.start();
    do { process(); if (condition()) return true; QThread::msleep(5); } while (timer.elapsed() < 3000);
    return false;
}
class MainWindow final : public ui::IMainWindow
{
public:
    explicit MainWindow(QWindow* window) : m_window(window) {}
    void init(ui::MainWindowBridge*) override {}
    void deinit() override {}
    QWindow* qWindow() const override { return m_window; }
    void requestShowOnBack() override {}
    void requestShowOnFront() override {}
    bool isFullScreen() const override { return false; }
    async::Notification isFullScreenChanged() const override { return {}; }
    void toggleFullScreen() override {}
    QScreen* screen() const override { return m_window->screen(); }
private:
    QWindow* m_window;
};
static QAccessibleInterface* named(QAccessibleInterface* parent, const QString& name)
{
    if (!parent || !parent->isValid()) return nullptr;
    if (parent->text(QAccessible::Name) == name) return parent;
    for (int i = 0; i < parent->childCount(); ++i)
        if (auto found = named(parent->child(i), name)) return found;
    return nullptr;
}
static QAccessibleInterface* namedBySibling(QAccessibleInterface* parent, const QString& name, int depth = 0)
{
    require(depth < 64, "accessible sibling traversal remains bounded");
    if (!parent || !parent->isValid() || parent->state().invisible) return nullptr;
    if (parent->text(QAccessible::Name) == name) return parent;
    // Qt6.11.2 Windows UIA Navigate uses the child's parent/indexOfChild to
    // obtain the next sibling, rather than iterating the original root's list.
    int index = 0;
    while (index < parent->childCount()) {
        auto child = parent->child(index);
        if (!child || !child->isValid() || child->state().invisible) { ++index; continue; }
        require(child->parent() == parent, "UIA sibling traversal must stay under the same accessible parent");
        const int parentIndex = child->parent()->indexOfChild(child);
        require(parentIndex == index, "UIA sibling navigation must find the same child index");
        if (auto found = namedBySibling(child, name, depth + 1)) return found;
        index = parentIndex + 1;
    }
    return nullptr;
}
static QObject* qmlObject(QObject* root, const QString& id)
{
    if (auto context = qmlContext(root))
        if (auto object = context->objectForName(id)) return object;
    for (auto child : root->children())
        if (auto object = qmlObject(child, id)) return object;
    return nullptr;
}
#include "recipe_dialog_accessibility_tests.h"
int main(int argc, char** argv)
{
    qputenv("QT_QPA_PLATFORM", "offscreen");
    qputenv("QML_DISABLE_DISK_CACHE", "1");
    // Windows offscreen uses FreeType, not the system Windows font database.
    // Give it the same existing source font on every host before any text layout.
    qputenv("QT_QPA_FONTDIR", WAVEQUAY_TEST_FONTS);
    qInfo() << "Onboarding probe: constructing QGuiApplication";
    QGuiApplication app(argc, argv);
    qInfo() << "Onboarding probe: application constructed";
    auto logger = kors::logger::Logger::instance();
    logger->clearDests();
    logger->addDest(new ProbeStderrLogDest());
    const int fontId = QFontDatabase::addApplicationFont(QStringLiteral(WAVEQUAY_TEST_FONTS "/FreeSerif.ttf"));
    require(fontId >= 0, "offscreen fixture font must register before QML loads");
    const QStringList fontFamilies = QFontDatabase::applicationFontFamilies(fontId);
    require(!fontFamilies.isEmpty(), "offscreen fixture font must expose a family");
    const QFont font(fontFamilies.front());
    const QRawFont resolvedFont = QRawFont::fromFont(font);
    require(resolvedFont.isValid() && resolvedFont.familyName() == fontFamilies.front()
            && resolvedFont.supportsCharacter(QChar('A')), "offscreen fixture must resolve the registered font, without a box fallback");
    QGuiApplication::setFont(font);
    qInfo().noquote() << "Onboarding probe: fixture font registered" << fontFamilies.front();
    // Register early, then let Qt Quick install its own factory during startup.
    // The second process also tests the opposite initialization order.
    registry.registerInterfaceGetter("QQuickWindow", AccessibilityController::accessibleInterface);
    registry.registerInterfaceGetter("muse::accessibility::AccessibleObject", AccessibleObject::accessibleInterface);
    registry.registerInterfaceGetter("muse::accessibility::AccessibleAppRootObject", AccessibleAppRootObject::accessibleInterface);
    au::appshell::registerDialogAccessibility(registry);
    QAccessible::installFactory(factory);
    QAccessible::installFactory(stockQuickFactory);
    QQmlEngine engine;
    qInfo() << "Onboarding probe: QML engine constructed";
    QQmlComponent mainComponent(&engine);
    std::unique_ptr<QQuickWindow> mainOwner;
    if (app.arguments().contains("--application-window")) {
        // AppWindow.qml's real Qt base, instead of the QQuickView popup class.
        mainComponent.setData("import QtQuick.Controls\nApplicationWindow { width: 800; height: 600 }", QUrl());
        mainOwner.reset(qobject_cast<QQuickWindow*>(mainComponent.create()));
        if (!mainOwner) qCritical() << mainComponent.errors();
        require(mainOwner != nullptr && mainOwner->inherits("QQuickApplicationWindow"), "real Qt ApplicationWindow main must load");
        require(QByteArray(mainOwner->metaObject()->className()) != "QQuickApplicationWindow", "QML must supply its actual derived metaobject");
    } else {
        mainOwner = std::make_unique<QQuickView>(&engine, nullptr);
    }
    QQuickWindow& mainWindow = *mainOwner;
    QQuickView popup(&engine, nullptr);
    require(!au::appshell::applicationWindowAccessibleFactory("QQuickApplicationWindow", nullptr)
            && !au::appshell::applicationWindowAccessibleFactory("QQuickView", &popup)
            && !au::appshell::applicationWindowAccessibleFactory("foreign", &mainWindow),
            "main-window factory must reject null, popup and unrelated class requests");
    if (app.arguments().contains("--muse-factory-last")) {
        QAccessible::removeFactory(factory); QAccessible::installFactory(factory);
    }
    auto appRoot = std::make_shared<AccessibleAppRootObject>();
    modularity::globalIoc()->registerExport<IAccessibleAppRootObject>("test", appRoot);
    auto ctx = std::make_shared<modularity::Context>(1);
    auto ioc = modularity::ioc(ctx);
    auto main = std::make_shared<MainWindow>(&mainWindow);
    auto accessibility = std::make_shared<AccessibilityController>(ctx);
    auto navigation = std::make_shared<ui::NavigationController>(ctx);
    auto commands = std::make_shared<rcommand::CommandDispatcher>();
    auto actions = std::make_shared<actions::ActionsDispatcher>(ctx);
    ioc->registerExport<ui::IMainWindow>("test", main);
    ioc->registerExport<IAccessibilityController>("test", accessibility);
    ioc->registerExport<ui::INavigationController>("test", navigation);
    ioc->registerExport<rcommand::ICommandDispatcher>("test", commands);
    ioc->registerExport<actions::IActionsDispatcher>("test", actions);
    auto configuration = std::make_shared<testing::NiceMock<au::appshell::AppShellConfigurationMock>>();
    auto interactive = std::make_shared<testing::NiceMock<muse::InteractiveMock>>();
    int completionWrites = 0;
    EXPECT_CALL(*configuration, setHasCompletedFirstLaunchSetup(true)).WillOnce([&](bool) { ++completionWrites; });
    ON_CALL(*interactive, open(testing::_)).WillByDefault([](const UriQuery&) {
        return async::make_promise<Val>([](auto resolve) { return resolve(Val()); });
    });
    modularity::globalIoc()->registerExport<au::appshell::IAppShellConfiguration>("test", configuration);
    ioc->registerExport<muse::IInteractive>("test", interactive);
    navigation->init();
    qInfo() << "Onboarding probe: navigation initialized";
    accessibility->setAccessibilityEnabled(true);
    // Qt Windows exposes ValuePattern even without a QAccessibleValueInterface.
    // Muse's actual editable content is supplied by its text interface instead.
    {
        ui::AccessibleItem edit(ctx);
        edit.setRole(ui::MUAccessible::EditableText);
        edit.setName("field label is not its text");
        AccessibleObject object(&edit);
        auto provider = QAccessible::queryAccessibleInterface(&object);
        require(provider && provider->role() == QAccessible::EditableText && provider->textInterface(),
                "actual Muse edit exposes its text interface");
        for (const auto& text : {QStringLiteral("D:\\a\\wavequay\\wavequay\\build-evidence\\gui\\consumer-fixture"),
                                QStringLiteral("reversed"), QStringLiteral("Dawn thread stereo")}) {
            edit.setText(text); // The same property bound to valueInput.text by production TextInputField.qml.
            auto content = provider->textInterface();
            require(provider->text(QAccessible::Value).isEmpty(), "Muse generic Value remains distinct from editable text");
            require(content->characterCount() == text.size() && content->text(0, content->characterCount()) == text,
                    "actual Muse text interface returns the complete current Folder, filename and recipe text");
        }
        qInfo() << "Muse editable text interface passed; generic Value is empty";
    }
    // Keep platform announcements inactive; provider state and focus lookup still run.
    QmlIoCContext iocContext(&engine); iocContext.ctx = ctx;
    engine.rootContext()->setContextProperty("ioc_context", &iocContext);
    engine.globalObject().setProperty("qsTrc", engine.evaluate("(function(context,text){return text;})"));
    QVariantMap theme;
    for (const auto key : {"largeBodyBoldFont", "bodyFont", "iconsFont"}) theme[key] = font;
    for (const auto key : {"backgroundPrimaryColor", "fontPrimaryColor", "buttonColor", "accentColor", "strokeColor"}) theme[key] = "#ffffff";
    for (const auto key : {"itemOpacityDisabled", "buttonOpacityNormal", "borderWidth", "buttonOpacityHit"}) theme[key] = 1.0;
    theme["defaultButtonSize"] = 28;
    engine.rootContext()->setContextProperty("ui", QVariantMap{{"theme", theme}});
    // The installed main window has its own accessible controls before opening
    // onboarding. Keep one present so a popup cannot borrow that window's tree.
    auto mainPanel = std::make_unique<ui::AccessibleItem>(ctx);
    mainPanel->setRole(ui::MUAccessible::Panel);
    mainPanel->setName("List");
    mainPanel->setVisualItem(mainWindow.contentItem());
    mainPanel->setState(IAccessible::State::Focused, true);
    mainPanel->componentComplete();
    auto mainFocus = std::make_unique<ui::AccessibleItem>(ctx);
    mainFocus->setAccessibleParent(mainPanel.get());
    mainFocus->setRole(ui::MUAccessible::Button);
    mainFocus->setName("Main editor focus");
    mainFocus->setVisualItem(mainWindow.contentItem());
    mainFocus->setState(IAccessible::State::Focused, true);
    mainFocus->componentComplete();
    qmlRegisterType<au::appshell::FirstLaunchSetupModel>("Audacity.AppShell", 1, 0, "FirstLaunchSetupModel");
    qmlRegisterType<ui::AccessibleItem>("Muse.Ui", 1, 0, "AccessibleItem");
    qmlRegisterType<ui::NavigationSection>("Muse.Ui", 1, 0, "NavigationSection");
    qmlRegisterType<ui::NavigationPanel>("Muse.Ui", 1, 0, "NavigationPanel");
    qmlRegisterType<ui::NavigationControl>("Muse.Ui", 1, 0, "NavigationControl");
    qmlRegisterUncreatableMetaObject(ui::MUAccessible::staticMetaObject, "Muse.Ui", 1, 0, "MUAccessible", "enum");
    qmlRegisterUncreatableType<ui::NavigationEvent>("Muse.Ui", 1, 0, "NavigationEvent", "event");
    engine.addImportPath(QStringLiteral(WAVEQUAY_TEST_IMPORTS));
    QQmlComponent component(&engine);
    component.setData("import Audacity.AppShell 1.0\nFirstLaunchSetupDialog {}", QUrl());
    QObject* dialog = component.create();
    qInfo() << "Onboarding probe: dialog component created";
    if (!dialog) qCritical() << component.errors();
    require(dialog, "production onboarding QML loads");
    auto item = dialog->property("contentItem").value<QQuickItem*>();
    popup.setTransientParent(&mainWindow);
    popup.setContent(QUrl(), &component, item);
    mainWindow.show(); popup.show(); popup.requestActivate();
    qInfo() << "Onboarding probe: offscreen views shown";
    process();
    QMetaObject::invokeMethod(dialog, "opened");
    process();
    auto windowInterface = QAccessible::queryAccessibleInterface(&popup);
    qInfo() << "Onboarding probe: popup interface queried";
    require(dynamic_cast<AccessibleWindowInterface*>(windowInterface), "QQuickView must use the registered Muse window provider");
    for (int index = 0; index < windowInterface->childCount(); ++index) {
        auto child = windowInterface->child(index);
        require(child && child->window() == &popup, "popup children must belong to the popup, not its transient parent");
        require(child->parent() == windowInterface && windowInterface->indexOfChild(child) == index,
                "popup children must preserve parent/indexOfChild round trips used by Windows UIA sibling navigation");
    }
    auto mainInterface = QAccessible::queryAccessibleInterface(&mainWindow);
    require(dynamic_cast<AccessibleWindowInterface*>(mainInterface), "main window must use Muse provider instead of stock Qt Quick provider");
    auto mainItemInterface = named(mainInterface, "List");
    require(mainItemInterface && !named(windowInterface, "List"), "main controls remain in their own window only");
    require(windowInterface->indexOfChild(mainItemInterface) == -1 && !windowInterface->child(-1)
            && !windowInterface->child(windowInterface->childCount()), "foreign children and out-of-range child indexes are rejected");
    require(namedBySibling(mainInterface, "Main editor focus") && mainInterface->focusChild(),
            "main editor controls and focus must remain reachable by Windows UIA sibling traversal");
    if (app.arguments().contains("--application-window")) qInfo() << "ApplicationWindow Muse provider and editor traversal passed";
    qInfo() << "Muse QQuickView provider selected; Qt" << qVersion();
    graphDiagnosticTests(windowInterface);
    auto model = qmlObject(dialog, "model");
    auto next = qobject_cast<QQuickItem*>(qmlObject(dialog, "nextStepButton"));
    require(model && next, "production model and Next identities resolve");
    const QStringList pages{"Select a theme. Next", "Clip visualization. Next", "What UI layout (workspace) do you want?. Accept & continue"};
    for (int index = 0; index < pages.size(); ++index) {
        bool focusedPage = waitUntil([&] { auto focus = windowInterface->focusChild(); return focus && focus->text(QAccessible::Name) == pages[index]; });
        if (!focusedPage) {
            auto focus = windowInterface->focusChild();
            auto page = dialog->property("currentPage").value<QObject*>();
            qCritical() << "Expected" << pages[index] << "actual" << (focus ? focus->text(QAccessible::Name) : "<none>")
                        << "page title" << (page ? page->property("title") : QVariant())
                        << "page button" << (page ? page->property("activeButtonTitle") : QVariant());
        }
        require(focusedPage, "popup focusChild reaches the exact current page surrogate");
        auto focus = windowInterface->focusChild();
        require(focus->role() == QAccessible::Button && !focus->state().disabled && focus->state().focused, "focused surrogate is an enabled Button");
        require(named(windowInterface, pages[index]) == focus, "focused surrogate is reachable in the popup tree");
        require(namedBySibling(windowInterface, pages[index]) == focus, "Windows UIA sibling traversal reaches the exact page surrogate");
        require(!focus->actionInterface(), "Muse surrogate must not acquire a second native Invoke route");
        auto page = dialog->property("currentPage").value<QQuickItem*>();
        {
            QAccessibleQuickItem nativePage(page), nativeNext(next);
            require(!nativePage.actionNames().contains(QAccessibleActionInterface::pressAction()), "page must not expose an unguarded duplicate native press action");
            require(!nativeNext.actionNames().contains(QAccessibleActionInterface::pressAction()), "Next must not expose a duplicate native press action");
            QMetaObject::invokeMethod(page, "resetFocus");
            require(windowInterface->focusChild() != focus, "resetFocus withdraws the surrogate from accessible focus lookup");
            nativePage.doAction(QAccessibleActionInterface::pressAction());
            nativeNext.doAction(QAccessibleActionInterface::pressAction());
            require(model->property("currentPageIndex").toInt() == index && completionWrites == 0, "withdrawn native actions cannot advance onboarding");
            for (const char* property : {"enabled", "visible"}) {
                page->setProperty(property, false);
                nativePage.doAction(QAccessibleActionInterface::pressAction());
                require(model->property("currentPageIndex").toInt() == index && completionWrites == 0, "disabled/hidden page has no alternate press route");
                page->setProperty(property, true);
            }
            QMetaObject::invokeMethod(page, "readInfo");
        }
        for (const char* property : {"enabled", "visible"}) {
            next->setProperty(property, false);
            commands->dispatch(ui::TRIGGER_CONTROL_COMMAND); process();
            require(model->property("currentPageIndex").toInt() == index && dialog->property("acceptCount").toInt() == 0, "disabled/hidden Next refuses the navigation action");
            next->setProperty(property, true);
        }
        require(navigation->activeControl() && navigation->activeControl()->name() == "NextButton", "surrogate reading retains Next as the real navigation target");
        commands->dispatch(ui::TRIGGER_CONTROL_COMMAND); process();
        require(model->property("currentPageIndex").toInt() == qMin(index+1, 2), "one navigation trigger advances exactly one page");
        require(dialog->property("acceptCount").toInt() == (index == 2 ? 1 : 0), "only Accept & continue accepts onboarding once");
        qInfo().noquote() << "Verified" << pages[index] << "focus, guarded trigger, and single transition";
    }
    require(completionWrites == 1, "completion is committed exactly once");
    require(testing::Mock::VerifyAndClearExpectations(configuration.get()), "configuration completion contract");
    delete dialog;
    popup.hide();
    process();
    mainInterface = QAccessible::queryAccessibleInterface(&mainWindow);
    require(dynamic_cast<AccessibleWindowInterface*>(mainInterface)
            && namedBySibling(mainInterface, "Main editor focus") && mainInterface->focusChild(),
            "main editor provider and sibling/focus routes survive onboarding destruction");
    recipeDialogAccessibilityTests(engine, mainWindow);
    mainFocus.reset();
    mainPanel.reset();
    qInfo() << "Onboarding probe: dialog destroyed";
    accessibility->deinit();
    modularity::resetAll();
    qInfo() << "Onboarding accessibility runtime passed";
    return 0;
}
